# Digi Setu

Monorepo for the Digi Setu coding agent. Wraps `pi-coding-agent` with a Typst-tuned tool surface, ships as a hosted Vue/FastAPI web app and as a cross-platform Tauri desktop app. The repo's filesystem path may still read `pi-typst-test/` for historical reasons; everything that surfaces to users — UI, binary names, deeplink scheme, support email — uses **Digi Setu**.

## Layout

- `extensions/typst-tools.ts` — registers `search_docs`, `web_search`, `open_url`, `list_fonts`, `list_packages`. Loaded automatically via `pi` field in `package.json`. Compiling and rendering use pi's built-in `bash` tool, not a wrapper.
- `guides/` — symlink to `../refernecs/typst-agent/guides`. The full indexed Typst documentation corpus (1,500+ files across 7 packages). `search_docs` reads from here.
- `workspace/` — sandbox for any artifacts the agent generates during a session. Treat anything outside `workspace/` as read-only context.
- `.pi/APPEND_SYSTEM.md` — Typst-specific guidance appended to pi's default coding-assistant prompt.
- `scripts/` — convenience runners that export the right env vars and launch pi.

## Conventions for the agent

- Generate Typst artifacts under `workspace/`, not at the repo root.
- Compile via `bash`: `typst compile --root . workspace/main.typ workspace/main.pdf`. To visually verify, render PNG (`--format png ... main-{n}.png`) and `read` each png before declaring done.
- When `search_docs` returns paths, you can read them directly with the built-in `read` tool — they live under `guides/`.
- Use the pinned import lines from `list_packages()`. Anything outside that set: validate empirically by compiling.
- For info outside the indexed corpus (real-world facts for the document, uncovered packages, recent events) use `web_search`. To open a URL the user pasted or a citation from `web_search`, use `open_url`.
