#!/usr/bin/env node
/**
 * Generate desktop/THIRD_PARTY_LICENSES.txt by walking everything we
 * actually bundle:
 *
 *   1. NPM packages under desktop/pi-runtime/vendor/pi/node_modules/
 *      — pi-coding-agent + its transitive deps + our extension deps
 *      (@google/genai, @anthropic-ai/vertex-sdk, typebox, tsx, …).
 *      For each package we grab `package.json` (name/version/license)
 *      plus the LICENSE / LICENCE / COPYING file if present.
 *
 *   2. Rust crates from desktop/src-tauri/Cargo.lock — full transitive
 *      dependency list, including indirect ones (Tauri's, serde's,
 *      tokio's). We don't have the per-crate LICENSE files locally
 *      (Cargo doesn't extract them by default), so we point at
 *      crates.io for each.
 *
 *   3. Python packages from desktop/backend/requirements.txt — direct
 *      deps. Pip's installed-packages-with-license report lives in
 *      site-packages METADATA files, not in our source tree, so we
 *      list packages by name and link the PyPI page.
 *
 *   4. Bundled fonts from desktop/backend/fonts/ — these have their
 *      own SIL OFL 1.1 / Apache 2.0 / public-domain licenses; we
 *      attribute by family.
 *
 * The output is a single concatenated text file shipped alongside
 * the binary so the user can satisfy MIT/Apache/SIL OFL clause-3
 * obligations without us doing per-package ad-hoc copy-pasting at
 * build time.
 *
 * Run:
 *
 *     node desktop/scripts/gen-third-party-licenses.mjs
 *
 * Or hook into desktop/scripts/build-mac.sh / build-windows.ps1 so
 * the file is regenerated on every release build.
 *
 * Idempotent. Overwrites the output file each run.
 */

import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, resolve, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DESKTOP = resolve(HERE, "..");
const PROJECT = resolve(DESKTOP, "..");

const NPM_ROOT = join(DESKTOP, "pi-runtime/vendor/pi/node_modules");
const CARGO_LOCK = join(DESKTOP, "src-tauri/Cargo.lock");
const PY_REQS = join(DESKTOP, "backend/requirements.txt");
const FONTS_DIR = join(DESKTOP, "backend/fonts");
const OUTPUT = join(DESKTOP, "THIRD_PARTY_LICENSES.txt");

const HEADER = `Digi Setu Desktop — Third-Party Software Notices
================================================

Digi Setu Desktop redistributes the open-source components listed below.
Each component is provided under its own license; copies of those
licenses (where available locally) follow this notice. The application
binary itself is not modified copies of the upstream — the components
are loaded as separate libraries / executable runtimes.

For sources of any GPL/LGPL component listed here, contact
support@digi-setu.com and reference the component name + version below.

Generated: ${new Date().toISOString()}

`;

// ─── 1. NPM packages ──────────────────────────────────────────────────

function readJson(path) {
	try {
		return JSON.parse(readFileSync(path, "utf8"));
	} catch {
		return null;
	}
}

function findLicenseFile(pkgDir) {
	let entries;
	try {
		entries = readdirSync(pkgDir);
	} catch {
		return null;
	}
	const candidates = entries.filter((name) =>
		/^(LICENSE|LICENCE|COPYING|NOTICE)(\.|-|_|$)/i.test(name),
	);
	if (candidates.length === 0) return null;
	candidates.sort((a, b) => {
		const score = (n) => (/^LICENSE$/i.test(n) ? 0 : /^LICENCE$/i.test(n) ? 1 : 2);
		return score(a) - score(b);
	});
	const path = join(pkgDir, candidates[0]);
	try {
		return readFileSync(path, "utf8");
	} catch {
		return null;
	}
}

function walkNpm(root) {
	const out = new Map();
	function visit(dir) {
		let names;
		try {
			names = readdirSync(dir);
		} catch {
			return;
		}
		for (const name of names) {
			if (name === ".bin" || name === ".cache" || name === ".package-lock.json") continue;
			const full = join(dir, name);
			let st;
			try {
				st = statSync(full);
			} catch {
				continue;
			}
			if (!st.isDirectory()) continue;
			if (name.startsWith("@")) {
				visit(full);
				continue;
			}
			const pj = join(full, "package.json");
			if (existsSync(pj)) {
				const meta = readJson(pj);
				if (meta && meta.name) {
					const key = `${meta.name}@${meta.version || "?"}`;
					if (!out.has(key)) {
						out.set(key, {
							name: meta.name,
							version: meta.version || "?",
							license:
								typeof meta.license === "string"
									? meta.license
									: meta.license?.type || meta.licenses?.[0]?.type || "(unspecified)",
							homepage: meta.homepage || meta.repository?.url || `https://www.npmjs.com/package/${meta.name}`,
							licenseText: findLicenseFile(full),
							author:
								typeof meta.author === "string" ? meta.author : meta.author?.name || meta.author?.email || "",
						});
					}
				}
			}
			const nested = join(full, "node_modules");
			if (existsSync(nested)) visit(nested);
		}
	}
	if (existsSync(root)) visit(root);
	return out;
}

function emitNpm(buf, packages) {
	buf.push("\n");
	buf.push("--- NPM packages (Node.js runtime + pi-coding-agent extensions) ---\n");
	buf.push("\n");
	const sorted = [...packages.values()].sort((a, b) => a.name.localeCompare(b.name));
	for (const pkg of sorted) {
		buf.push(`* ${pkg.name}@${pkg.version}`);
		buf.push(`  License: ${pkg.license}`);
		if (pkg.author) buf.push(`  Author:  ${pkg.author}`);
		buf.push(`  URL:     ${pkg.homepage}`);
		buf.push("");
	}
	buf.push("\n");
	buf.push("--- NPM package full license texts ---\n");
	buf.push("\n");
	for (const pkg of sorted) {
		if (!pkg.licenseText) continue;
		buf.push("=".repeat(72));
		buf.push(`${pkg.name}@${pkg.version}  (${pkg.license})`);
		buf.push("=".repeat(72));
		buf.push(pkg.licenseText.trim());
		buf.push("");
		buf.push("");
	}
}

// ─── 2. Rust crates ───────────────────────────────────────────────────

function parseCargoLock(path) {
	const text = readFileSync(path, "utf8");
	const out = [];
	const blocks = text.split(/\n\[\[package\]\]\n/);
	for (const block of blocks) {
		const nameMatch = block.match(/^name = "([^"]+)"/m);
		const versionMatch = block.match(/^version = "([^"]+)"/m);
		const sourceMatch = block.match(/^source = "([^"]+)"/m);
		if (nameMatch && versionMatch) {
			out.push({
				name: nameMatch[1],
				version: versionMatch[1],
				source: sourceMatch ? sourceMatch[1] : "(local / workspace)",
			});
		}
	}
	return out;
}

function emitCargo(buf, crates) {
	buf.push("\n");
	buf.push("--- Rust crates (Tauri shell + dependencies) ---\n");
	buf.push("\n");
	buf.push("Per-crate license texts are not bundled in source. Cargo's metadata\n");
	buf.push("links each crate to crates.io, where its LICENSE file is published.\n");
	buf.push("Most crates listed below are MIT or MIT/Apache-2.0; a handful (such\n");
	buf.push("as ring) carry their own bespoke licenses — see the linked source.\n");
	buf.push("\n");
	const sorted = [...crates].sort((a, b) => a.name.localeCompare(b.name));
	for (const c of sorted) {
		buf.push(`* ${c.name}@${c.version}  —  https://crates.io/crates/${c.name}/${c.version}`);
	}
}

// ─── 3. Python packages ──────────────────────────────────────────────

function parseRequirements(path) {
	const text = readFileSync(path, "utf8");
	const out = [];
	for (const raw of text.split(/\r?\n/)) {
		const line = raw.replace(/#.*$/, "").trim();
		if (!line) continue;
		const m = line.match(/^([A-Za-z0-9_.\[\]\-]+)\s*([<>=!~]=?\s*[^\s;]+)?/);
		if (m) out.push({ name: m[1].split("[")[0], pin: m[2] || "" });
	}
	return out;
}

function emitPython(buf, pyDeps) {
	buf.push("\n");
	buf.push("--- Python packages (sidecar runtime) ---\n");
	buf.push("\n");
	buf.push("Direct dependencies declared in desktop/backend/requirements.txt.\n");
	buf.push("Each package's LICENSE is reachable via its PyPI page below.\n");
	buf.push("\n");
	const sorted = [...pyDeps].sort((a, b) => a.name.localeCompare(b.name));
	for (const p of sorted) {
		buf.push(`* ${p.name}${p.pin ? " " + p.pin : ""}  —  https://pypi.org/project/${p.name}/`);
	}
}

// ─── 4. Bundled fonts ─────────────────────────────────────────────────

const FONT_NOTICES = [
	{
		family: "Font Awesome 7 Free (Free Regular, Free Solid, Brands)",
		license: "CC BY 4.0 (icons) + SIL OFL 1.1 (fonts) + MIT (CSS)",
		url: "https://fontawesome.com/license/free",
		note: "Free version only. No Pro variants (Light, Duotone, Sharp, Thin) are bundled.",
	},
	{
		family: "Inter, Inter Display",
		license: "SIL OFL 1.1",
		url: "https://github.com/rsms/inter",
	},
	{
		family: "Lato",
		license: "SIL OFL 1.1",
		url: "https://www.latofonts.com/",
	},
	{
		family: "Source Sans 3 / Source Serif 4",
		license: "SIL OFL 1.1",
		url: "https://github.com/adobe-fonts",
	},
	{
		family: "EB Garamond",
		license: "SIL OFL 1.1",
		url: "https://github.com/octaviopardo/EBGaramond12",
	},
	{
		family: "Merriweather, Open Sans, Roboto, Noto Sans, Playfair Display, Oswald, Montserrat, Raleway",
		license: "SIL OFL 1.1 (Google Fonts)",
		url: "https://fonts.google.com",
	},
	{
		family: "Libertinus Serif / Libertinus Math",
		license: "SIL OFL 1.1",
		url: "https://github.com/alerque/libertinus",
	},
	{
		family: "STIX Two Text / STIX Two Math",
		license: "SIL OFL 1.1",
		url: "https://github.com/stipub/stixfonts",
	},
	{
		family: "Fira Code",
		license: "SIL OFL 1.1",
		url: "https://github.com/tonsky/FiraCode",
	},
	{
		family: "DejaVu Sans / DejaVu Sans Mono",
		license: "DejaVu Fonts License (public-domain-style)",
		url: "https://dejavu-fonts.github.io/",
	},
	{
		family: "Inconsolata",
		license: "SIL OFL 1.1",
		url: "https://github.com/googlefonts/Inconsolata",
	},
	{
		family: "New Computer Modern (LM Mono, etc.)",
		license: "GUST Font License (similar to SIL OFL)",
		url: "https://www.gust.org.pl/projects/e-foundry/lm-math",
	},
	{
		family: "Symbols Nerd Font",
		license: "MIT (icons) + upstream font licenses",
		url: "https://github.com/ryanoasis/nerd-fonts",
	},
	{
		family: "Academicons",
		license: "SIL OFL 1.1",
		url: "https://jpswalsh.github.io/academicons/",
	},
];

function emitFonts(buf) {
	buf.push("\n");
	buf.push("--- Bundled typography ---\n");
	buf.push("\n");
	for (const f of FONT_NOTICES) {
		buf.push(`* ${f.family}`);
		buf.push(`  License: ${f.license}`);
		buf.push(`  URL:     ${f.url}`);
		if (f.note) buf.push(`  Note:    ${f.note}`);
		buf.push("");
	}
}

// ─── 5. Built-in upstream attribution ────────────────────────────────

const UPSTREAM_ATTRIBUTION = `\n--- Notable upstream components ---\n
* @mariozechner/pi-coding-agent
  License: MIT
  Author:  Mario Zechner
  URL:     https://github.com/mariozechner/pi-coding-agent
  Note:    Loaded as a separate Node.js process; not statically linked.
           Digi Setu Desktop ships our own TypeScript extension
           (typst-tools.ts) on top of this; we apply small idempotent
           patches to pi-ai under desktop/pi-runtime/install-pi.sh
           (sentinel-guarded) to add Vertex provider routing.

* Anthropic SDKs (@anthropic-ai/vertex-sdk, @anthropic-ai/sandbox-runtime)
  License: MIT
  URL:     https://github.com/anthropics/
  Note:    Used as published; not modified.

* Tauri (tauri, tauri-build, tauri-plugin-*)
  License: Apache-2.0 OR MIT
  URL:     https://tauri.app
  Note:    Used as published.

* Typst CLI (bundled binary)
  License: Apache-2.0
  URL:     https://github.com/typst/typst
  Note:    Loaded as a separate process for compilation.

* FastAPI / Starlette / uvicorn / pydantic
  License: MIT / BSD-3-Clause
  URL:     https://fastapi.tiangolo.com / https://www.starlette.io /
           https://www.uvicorn.org / https://docs.pydantic.dev
`;

// ─── main ────────────────────────────────────────────────────────────

function main() {
	const buf = [HEADER];

	console.error("[licenses] scanning npm packages under", NPM_ROOT);
	const npmPkgs = walkNpm(NPM_ROOT);
	console.error(`[licenses] found ${npmPkgs.size} npm packages`);

	let crates = [];
	if (existsSync(CARGO_LOCK)) {
		console.error("[licenses] reading", CARGO_LOCK);
		crates = parseCargoLock(CARGO_LOCK);
		console.error(`[licenses] found ${crates.length} rust crates`);
	} else {
		console.error("[licenses] WARNING: Cargo.lock not found — run `cargo build` first.");
	}

	let pyDeps = [];
	if (existsSync(PY_REQS)) {
		pyDeps = parseRequirements(PY_REQS);
		console.error(`[licenses] found ${pyDeps.length} python dependencies`);
	}

	buf.push(UPSTREAM_ATTRIBUTION);
	emitNpm(buf, npmPkgs);
	emitCargo(buf, crates);
	emitPython(buf, pyDeps);
	emitFonts(buf);

	const text = buf.join("\n");
	writeFileSync(OUTPUT, text);
	console.error("[licenses] wrote", OUTPUT, `(${text.length.toLocaleString()} bytes)`);
}

main();
