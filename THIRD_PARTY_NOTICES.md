# Third-Party Notices

Digi Setu (the web editor at `digi-setu.com`, the Tauri-based desktop app
under `desktop/`, and the `pi-coding-agent` runtime configured under
`extensions/`) ships with, depends on, or vendors the open-source
software listed below. We're grateful to every author and maintainer.

This file is the canonical attribution document. The in-app
**Acknowledgements** page (`/acknowledgements` in both the web editor
and the desktop binary) renders the same information for end users.

If a notice here is wrong, missing, or you believe we're using your
work in a way that the license below does not permit, please email
**support@digi-setu.com** — we will fix it promptly.

---

## How licences map to what we ship

| Licence type | Effect on us | Components |
|---|---|---|
| **MIT** | Keep the copyright + permission text alongside the binary. | Touying, Fletcher, Codly, Quill, Tabler Icons |
| **Apache 2.0** | Same as MIT, plus we keep any `NOTICE` files. | Typst, Circuiteria |
| **LGPL v3** | Library may be used commercially. End users must be able to replace our shipped copy with their own modified copy. We do not modify the library. | CeTZ |
| **OFL 1.1** | Fonts may be embedded and redistributed inside Digi Setu, but cannot be sold as a standalone font product. | Source Sans 3, Noto Color Emoji |

The full text of each licence lives next to the corresponding package
under `guides/<package>/LICENSE` in this repository, and a copy is
included in every Digi Setu release artifact.

---

## Typst typesetting system

* **Project:** [Typst](https://typst.app)
* **Version vendored:** `0.14.2`
* **Licence:** Apache License 2.0
* **Source / licence:** [`guides/typst-0.14.2/LICENSE`](./guides/typst-0.14.2/LICENSE)
* **Copyright:** © The Typst Project Developers

Used as the underlying typesetting engine compiled and invoked by the
agent's `compile_typ` tool. Distributed under the terms of Apache 2.0.

## Typst packages

### Touying — slide / presentation framework

* **Version vendored:** `0.7.3`
* **Licence:** MIT
* **Source / licence:** [`guides/touying-0.7.3/LICENSE`](./guides/touying-0.7.3/LICENSE)
* **Copyright:** © 2026 OrangeX4, © 2026 zral0kh

### CeTZ — drawing & charts

* **Version vendored:** `0.5.0`
* **Licence:** GNU Lesser General Public License v3.0 (LGPL-3.0)
* **Source / licence:** [`guides/cetz-0.5.0/LICENSE`](./guides/cetz-0.5.0/LICENSE)
* **Copyright:** © The CeTZ Authors

CeTZ is the only component in Digi Setu under a copyleft licence.
Practical implications:

1. **You may use Digi Setu commercially.** LGPL permits use, distribution,
   and inclusion in a larger work that is itself proprietary.
2. **We do not modify CeTZ.** Digi Setu invokes CeTZ as a Typst package
   via the standard Typst package mechanism; the library code is shipped
   verbatim.
3. **You may replace CeTZ in any Digi Setu install.** CeTZ lives in the
   standard Typst packages directory inside the binary's data folder.
   Drop a different version (or your own modified version) of
   `cetz` in there and Digi Setu will load it instead. We rely on this
   replaceability to satisfy LGPL's "section 4d" requirement.
4. If we ever ship local modifications to CeTZ, those modifications will
   be released under LGPL alongside the next release.

### Fletcher — diagrams

* **Version vendored:** `0.5.8`
* **Licence:** MIT
* **Source / licence:** [`guides/fletcher-0.5.8/LICENSE`](./guides/fletcher-0.5.8/LICENSE)
* **Copyright:** © 2023 Joseph Wilson

### Codly — code listings

* **Version vendored:** `1.3.0`
* **Licence:** MIT
* **Source / licence:** [`guides/codly-1.3.0/LICENSE`](./guides/codly-1.3.0/LICENSE)
* **Copyright:** © 2023 Sébastien d'Herbais de Thun, et al.

### Quill — quantum-circuit diagrams

* **Version vendored:** `0.7.2`
* **Licence:** MIT
* **Source / licence:** [`guides/quill-0.7.2/LICENSE`](./guides/quill-0.7.2/LICENSE)
* **Copyright:** © 2023-2025 Mc-Zen

### Circuiteria — electronic-circuit diagrams

* **Version vendored:** `0.2.0`
* **Licence:** Apache License 2.0
* **Source / licence:** [`guides/circuiteria-0.2.0/LICENSE`](./guides/circuiteria-0.2.0/LICENSE)
* **Copyright:** © The Circuiteria Authors

## Fonts

Bundled with the Codly documentation and used by the agent for code
listings and document samples.

| Font | Licence | Path |
|---|---|---|
| **Tabler Icons** | MIT | [`guides/codly-1.3.0/docs/fonts/Tabler Icons/LICENSE`](./guides/codly-1.3.0/docs/fonts/Tabler%20Icons/LICENSE) |
| **Source Sans 3** | SIL Open Font License 1.1 | [`guides/codly-1.3.0/docs/fonts/Source Sans 3/LICENSE`](./guides/codly-1.3.0/docs/fonts/Source%20Sans%203/LICENSE) |
| **Noto Color Emoji** | SIL Open Font License 1.1 | [`guides/codly-1.3.0/docs/fonts/Noto Color Emoji/LICENSE`](./guides/codly-1.3.0/docs/fonts/Noto%20Color%20Emoji/LICENSE) |

The OFL permits embedding and redistribution of the fonts inside Digi
Setu but forbids selling the font files on their own. We do neither.

---

## Application-level dependencies

Beyond the Typst stack above, Digi Setu's web and desktop frontends
depend on a large set of npm and Python packages — full machine-readable
manifests live in `web/frontend/package.json`,
`desktop/frontend/package.json`, `web/backend/requirements.txt`,
`desktop/backend/requirements.txt`, and `desktop/src-tauri/Cargo.toml`.

Notable user-facing components include:

| Component | Role | Licence |
|---|---|---|
| Vue.js | Frontend framework | MIT |
| Tauri | Desktop shell | MIT / Apache-2.0 |
| FastAPI | Backend HTTP layer | MIT |
| pi-coding-agent | Agent runtime | (vendor licence — see vendor) |
| Iconify (Codicon) | Icon set | MIT |
| Stripe SDK | Billing | MIT |
| Clerk SDK | Authentication | MIT |

For the full transitive set, run `npm ls` / `pip list --format=json` /
`cargo tree` against the respective sub-projects; every package's own
LICENSE file ships inside its `node_modules` / site-packages /
`Cargo.lock`-resolved source.

---

## Custom content authored by Digi Setu

Everything outside `guides/` and outside third-party `node_modules` /
`site-packages` directories — including the application source code,
the `.pi/APPEND_SYSTEM.md` agent persona, this notices file, and the
in-app prose under `web/frontend/src/views/` and
`desktop/frontend/src/views/` — is © 2025 Digi Setu. It is not
covered by the licences above.

---

## Legal notice on AI-generated output

Digi Setu's agent uses third-party large language models (currently
Anthropic Claude via Vertex AI, with Google Gemini and OpenAI as
fallbacks) to generate Typst documents, code, and prose on the user's
behalf. Output produced by an LLM may, in some jurisdictions (most
notably the United States, per the U.S. Copyright Office's 2023
guidance), not be eligible for copyright protection in its raw,
purely-machine-generated form. Users are responsible for reviewing,
editing, and verifying generated content before relying on it for any
purpose where authorship attribution or downstream IP claims matter.

See **Terms** (`/terms`) for the full output-ownership clause and the
acceptable-use boundaries.
