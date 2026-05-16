/**
 * desktop-protected-paths.ts — strict path guard for the DESKTOP runtime.
 *
 * Pi ships a default `protected-paths.ts` example that only blocks
 * `.env`, `.git/`, `node_modules/`. That's fine for the web container
 * (it's already filesystem-isolated to a per-session bind mount) but on
 * the user's actual laptop the AI can read `~/.ssh/id_rsa`, dump browser
 * cookies, exfiltrate cloud credentials, etc. unless we widen the
 * blocklist. This extension replaces pi's stock one on desktop.
 *
 * Hooked into `tool_call` for write|edit|read|grep|ls|find — anything
 * that touches the filesystem. Returns `{ block: true, reason }` for
 * any path matching the deny list. The denial surfaces as a
 * `tool_call_blocked` event the SPA already renders; the AI sees the
 * reason string and can ask the user for help instead of trying again.
 *
 * NOTE: this is a SECONDARY safety net. The primary defenses are
 *   1. macOS / Windows / Linux file permissions (the user already
 *      controls who can read what — running pi as their normal user
 *      account means `id_rsa` is mode 600 and the AI can't read it
 *      anyway). We just refuse to even TRY so the model doesn't
 *      learn that surfacing perms-denied errors is normal.
 *   2. The Python `services/policy.py` blocklist for bash patterns
 *      (sudo, cloud-metadata IPs, …) that catches secrets exfil
 *      attempts even when the path is "innocent" (e.g. piping
 *      `tar` through `curl`).
 */

import os from "node:os";
import path from "node:path";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const HOME = os.homedir();

/**
 * Substring patterns checked against the resolved absolute path of every
 * fs-touching tool call. Patterns are case-INSENSITIVE on macOS / Windows
 * (where FS itself is case-insensitive); on Linux they're case-sensitive.
 *
 * Grouped by what they protect so the deny reason can name the category.
 */
interface DenyRule {
	pattern: string;
	category: string;
}

const DENY_RULES: DenyRule[] = [
	// Pi defaults — keep parity with examples/extensions/protected-paths.ts
	{ pattern: "/.env", category: "env-file" },
	{ pattern: "/.env.", category: "env-file" }, // .env.local, .env.production, …
	{ pattern: "/.git/", category: "git-internals" },
	{ pattern: "/node_modules/", category: "build-artifact" },

	// SSH — the obvious one
	{ pattern: `${HOME}/.ssh/`, category: "ssh" },
	{ pattern: `${HOME}\\.ssh\\`, category: "ssh" }, // Windows path style

	// Cloud creds
	{ pattern: `${HOME}/.aws/`, category: "aws-creds" },
	{ pattern: `${HOME}/.azure/`, category: "azure-creds" },
	{ pattern: `${HOME}/.config/gcloud/`, category: "gcloud-creds" },
	{ pattern: `${HOME}/.kube/`, category: "kubernetes-creds" },
	{ pattern: `${HOME}/.docker/config.json`, category: "docker-creds" },
	{ pattern: `${HOME}/.netrc`, category: "netrc" },
	{ pattern: `${HOME}/.npmrc`, category: "npm-token" },
	{ pattern: `${HOME}/.pypirc`, category: "pypi-token" },

	// GPG / age / signing
	{ pattern: `${HOME}/.gnupg/`, category: "gpg" },
	{ pattern: `${HOME}/.age/`, category: "age-keys" },

	// macOS keychain & system stores
	{ pattern: `${HOME}/Library/Keychains/`, category: "keychain" },
	{ pattern: `${HOME}/Library/Cookies/`, category: "browser-cookies" },
	{ pattern: `${HOME}/Library/Application Support/Google/Chrome/`, category: "browser-data" },
	{ pattern: `${HOME}/Library/Application Support/Firefox/`, category: "browser-data" },
	{ pattern: `${HOME}/Library/Application Support/com.apple.TCC`, category: "tcc-database" },
	{ pattern: "/private/etc/sudoers", category: "system-config" },
	{ pattern: "/etc/sudoers", category: "system-config" },
	{ pattern: "/etc/shadow", category: "system-config" },

	// Linux desktop browser data
	{ pattern: `${HOME}/.config/google-chrome/`, category: "browser-data" },
	{ pattern: `${HOME}/.config/chromium/`, category: "browser-data" },
	{ pattern: `${HOME}/.mozilla/firefox/`, category: "browser-data" },

	// Password managers
	{ pattern: `${HOME}/.config/1Password/`, category: "1password" },
	{ pattern: `${HOME}/.config/Bitwarden/`, category: "bitwarden" },
	{ pattern: `${HOME}/Library/Containers/com.bitwarden.desktop/`, category: "bitwarden" },
	{ pattern: `${HOME}/Library/Group Containers/2BUA8C4S2C.com.1password/`, category: "1password" },

	// Windows equivalents (covered by case-insensitive matcher on win32)
	{ pattern: "/AppData/Roaming/Microsoft/Credentials/", category: "windows-creds" },
	{ pattern: "/AppData/Local/Google/Chrome/User Data/", category: "browser-data" },

	// ── App-credential dirs (added 2026-05-16) ────────────────────────
	// Pi itself stores Clerk session JWT + provider auth in `~/.pi/agent/auth.json`.
	// Our own desktop app stores user keys in `~/.digi-setu/`. Cursor
	// stores agent transcripts (including past prompts to other AIs) in
	// `~/.cursor/`. Anthropic / Claude desktop apps drop tokens in
	// `~/.config/anthropic/` and `~/Library/Application Support/Claude/`.
	// None of these are useful to the model and ALL of them contain
	// secrets that exfil cleanly via prompt injection. Block the dirs
	// entirely so the AI can't even enumerate filenames inside them.
	{ pattern: `${HOME}/.pi/`, category: "pi-creds" },
	{ pattern: `${HOME}/.digi-setu/`, category: "digi-setu-creds" },
	{ pattern: `${HOME}/.cursor/`, category: "cursor-data" },
	{ pattern: `${HOME}/.config/anthropic/`, category: "anthropic-creds" },
	{ pattern: `${HOME}/Library/Application Support/Claude/`, category: "claude-app-data" },
	{ pattern: `${HOME}/.codeium/`, category: "codeium-creds" },
	{ pattern: `${HOME}/.continue/`, category: "continue-creds" },
	{ pattern: `${HOME}/.copilot/`, category: "copilot-creds" },
	{ pattern: `${HOME}/.config/github-copilot/`, category: "copilot-creds" },

	// ── Random secrets people scatter in $HOME ─────────────────────────
	// These are commonly-named secret stashes that aren't covered by a
	// dotdir above. We block reads to them by-path; the basename regexes
	// below catch the same files in random locations.
	{ pattern: `${HOME}/.bash_history`, category: "shell-history" },
	{ pattern: `${HOME}/.zsh_history`, category: "shell-history" },
	{ pattern: `${HOME}/.fish_history`, category: "shell-history" },
	{ pattern: `${HOME}/.psql_history`, category: "shell-history" },
	{ pattern: `${HOME}/.python_history`, category: "shell-history" },
	{ pattern: `${HOME}/.lesshst`, category: "shell-history" },
	{ pattern: `${HOME}/.viminfo`, category: "shell-history" },
];

/**
 * Filename patterns — checked against the basename of the resolved path.
 * Catches things like `~/Desktop/id_rsa` that aren't under `~/.ssh/`.
 */
const DENY_BASENAME_PATTERNS: { pattern: RegExp; category: string }[] = [
	{ pattern: /^id_(rsa|dsa|ed25519|ecdsa)(\.pub)?$/i, category: "ssh-key" },
	{ pattern: /\.pem$/i, category: "private-key" },
	{ pattern: /\.p12$/i, category: "private-key" },
	{ pattern: /\.pfx$/i, category: "private-key" },
	{ pattern: /^known_hosts$/i, category: "ssh-known-hosts" },
];

/**
 * Tools to gate. Pi's tool-call event fires BEFORE execution, so blocking
 * here prevents the read from happening at all.
 *
 * read    → blocks reading secrets
 * grep    → blocks searching INSIDE secret paths (the matches would leak
 *           credentials into the model's context window)
 * find/ls → blocks ENUMERATING secret directories (so the AI doesn't even
 *           learn what private keys exist)
 * write/edit → blocks writing to system locations / overwriting secrets
 * bash    → blocks shell-piped reads (cat / head / tail / less / strings
 *           / awk / sed / xxd) — pi's `bash` is the obvious bypass for
 *           every path-based tool gate above. We parse the command and
 *           refuse if it references any DENY_RULES pattern. NOT a full
 *           sandbox (a determined attacker can base64-encode the path,
 *           assemble it via variables, etc.) but stops the casual
 *           `cat ~/.ssh/id_rsa` flow that prompt-injection attacks use.
 */
const GATED_TOOLS = new Set([
	"read",
	"grep",
	"find",
	"ls",
	"write",
	"edit",
	"bash",
]);

/**
 * Field the path lives in per-tool. Pi's tool inputs aren't uniform:
 *   read/write/edit → input.path
 *   grep            → input.path (folder/file to search)
 *   find            → input.path (root to search)
 *   ls              → input.path
 *   bash            → input.command (we sniff the *whole* command line
 *                     for any protected pattern; expansion of ~, $HOME
 *                     happens with the runtime $HOME the user is in)
 */
function extractPath(toolName: string, input: Record<string, unknown>): string | undefined {
	if (toolName === "bash") {
		const cmd = input.command ?? input.cmd ?? input.script;
		if (typeof cmd !== "string") return undefined;
		// Expand ~ → $HOME so DENY_RULES patterns that include the literal
		// $HOME prefix match shell-side `~/.foo` references. We don't do
		// a full shell parse — just the obvious tilde and $HOME
		// substitution — because deeper parsing (subshells, command
		// substitution, base64) is unreliable here. The Python-side
		// `services/policy.py` blocks more elaborate bypass attempts.
		return cmd
			.replace(/(^|[\s=:'"`(])~\//g, `$1${HOME}/`)
			.replace(/\$\{?HOME\}?\//g, `${HOME}/`);
	}
	const p = input.path ?? input.file ?? input.dir;
	return typeof p === "string" ? p : undefined;
}

function isCaseInsensitive(): boolean {
	return process.platform === "darwin" || process.platform === "win32";
}

/**
 * For path-shaped inputs (read/grep/find/ls/write/edit), resolve to an
 * absolute path so relative inputs like `../../.ssh/` get caught. For
 * bash commands we leave the string as-is — the input has already been
 * tilde/$HOME-expanded by extractPath() and substring matching against
 * the raw command line is exactly what we want (we'd lose the spaces
 * if we ran path.resolve on the whole bash invocation).
 */
function normalize(toolName: string, p: string): string {
	let s: string;
	if (toolName === "bash") {
		s = p;
	} else {
		try {
			s = path.resolve(p);
		} catch {
			s = p;
		}
	}
	return isCaseInsensitive() ? s.toLowerCase() : s;
}

function matchRule(haystack: string): DenyRule | undefined {
	const needles = isCaseInsensitive() ? DENY_RULES.map((r) => ({ ...r, pattern: r.pattern.toLowerCase() })) : DENY_RULES;
	return needles.find((r) => haystack.includes(r.pattern));
}

/**
 * For path inputs this checks the basename of the resolved path. For
 * bash inputs we run every basename regex against the whole command
 * line so `cat ~/Desktop/id_rsa` gets caught even though the basename
 * lookup wouldn't naturally apply to a shell string.
 */
function matchBasename(toolName: string, normalized: string): { pattern: RegExp; category: string } | undefined {
	if (toolName === "bash") {
		// Match each regex against the command line; if any private-key
		// looking token appears, flag it. We use `\b` so `id_rsa` matches
		// but `something_id_rsa` doesn't.
		return DENY_BASENAME_PATTERNS.find((r) => {
			const src = r.pattern.source;
			const flags = r.pattern.flags.includes("g") ? r.pattern.flags : r.pattern.flags + "g";
			const wrapped = new RegExp(`\\b${src.replace(/^\^/, "").replace(/\$$/, "")}\\b`, flags);
			return wrapped.test(normalized);
		});
	}
	const base = path.basename(normalized);
	return DENY_BASENAME_PATTERNS.find((r) => r.pattern.test(base));
}

export default function (pi: ExtensionAPI) {
	pi.on("tool_call", async (event, ctx) => {
		if (!GATED_TOOLS.has(event.toolName)) return undefined;

		const raw = extractPath(event.toolName, event.input as Record<string, unknown>);
		if (!raw) return undefined;

		const abs = normalize(event.toolName, raw);

		const ruleHit = matchRule(abs);
		const baseHit = matchBasename(event.toolName, abs);
		const hit = ruleHit ?? baseHit;
		if (!hit) return undefined;

		const reason = `Blocked: "${raw}" is under a protected category (${hit.category}). ` +
			`Desktop pi will not read or modify this kind of file. Ask the user for the ` +
			`specific value you need instead.`;

		if (ctx.hasUI) {
			ctx.ui.notify(`Blocked ${event.toolName} on ${hit.category}`, "warning");
		}

		return { block: true, reason };
	});
}
