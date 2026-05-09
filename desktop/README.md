# Digi Setu desktop

A Tauri shell that wraps the existing `web/` codebase as a native macOS +
Windows application. Same FastAPI backend, same Vue 3 SPA — frozen and
shipped as a single drag-to-Applications binary, with a bundled Node.js
runtime and pi-coding-agent install so users don't need anything on
their machine besides the .dmg / .msi.

The web app is the source of truth. Everything in `web/backend/` and
`web/frontend/` ships unchanged into the desktop bundle; this folder
adds **only** the Tauri Rust shell, a PyInstaller sidecar wrapping the
backend, and a vendored Node + pi runtime. Bug fixes auto-propagate to
both products on the next desktop build.

## Layout

```
desktop/
├── src-tauri/                 Rust shell (wry webview + sidecar mgmt)
│   ├── src/
│   │   ├── main.rs            entry point
│   │   ├── lib.rs             Tauri builder, plugin wiring, lifecycle
│   │   ├── sidecar.rs         spawn FastAPI binary, port discovery, kill on exit
│   │   ├── deeplink.rs        digi-setu://… URL scheme handler
│   │   └── commands.rs        IPC: pick_folder, get_backend_port, open_external_url
│   ├── capabilities/          Tauri v2 permission grants for the webview
│   ├── icons/                 .icns / .ico / @2x PNGs (regen via `tauri icon`)
│   ├── tauri.conf.json
│   └── Cargo.toml
├── sidecar/                   PyInstaller-frozen FastAPI backend
│   ├── sidecar_main.py        thin entry that imports `web/backend/app.py`
│   ├── pyinstaller.spec
│   ├── build_sidecar.sh       Mac/Linux build
│   ├── build_sidecar.ps1      Windows build
│   └── dist/                  output (gitignored)
├── pi-runtime/                Bundled Node.js + pi-coding-agent
│   ├── fetch-node.sh          downloads Node 22 LTS for every platform
│   ├── fetch-node.ps1
│   ├── install-pi.sh          npm-installs pi-coding-agent + extension deps
│   ├── install-pi.ps1
│   └── vendor/                node-<plat>/ + pi/ + extensions/ (gitignored)
├── scripts/
│   ├── build-mac.sh           one-command release build → .dmg
│   └── build-windows.ps1      one-command release build → .msi + setup.exe
├── package.json               npm scripts (dev / build / sidecar:build / …)
└── README.md                  this file
```

## Prerequisites

| Tool | Why | Notes |
|---|---|---|
| **Rust 1.77+** | Tauri shell compiles to native | `rustup install stable` |
| **Node 22+** | Frontend build + Tauri CLI | The bundled Node 22 in `pi-runtime/` is for **runtime**, not build |
| **Python 3.11** | Backend `web/backend/.venv` | Already required for `web/` dev |
| **Xcode CLI** (Mac only) | wry compiles against the macOS SDK | `xcode-select --install` |
| **VS 2022 Build Tools** (Win only) | MSVC linker for Tauri/wry | "Desktop development with C++" workload |

Make sure `web/backend/.venv` exists (`cd web/backend && python3 -m venv
.venv && source .venv/bin/activate && pip install -r requirements.txt`)
before running any of the desktop scripts — `build_sidecar.sh` reuses it.

## First-time setup

```bash
cd desktop
npm install                       # Tauri CLI + plugin packages
npm run pi-runtime:fetch          # Node + pi-coding-agent (~80 MB)
npm run sidecar:build             # PyInstaller-freeze the backend (~30s)
```

On Windows, swap `:fetch` and `:build` for their `:fetch:win` /
`build_sidecar.ps1` counterparts.

## Daily dev loop

```bash
cd desktop
npm run dev
```

This:
1. Starts the Vite dev server (web/frontend) on `127.0.0.1:5173`.
2. Compiles the Tauri shell (Rust).
3. Launches the desktop window pointing at the dev server.
4. Spawns the PyInstaller-frozen sidecar on a free local port and waits
   for `/healthz` before letting the SPA call API endpoints.

Live reload works for the SPA (Vite HMR). Changes to `src-tauri/`
(Rust) require killing the window and re-running `npm run dev`.
Changes to `web/backend/` require `npm run sidecar:build` to refreeze
the binary; the Tauri shell picks up the new file on next launch.

## Release builds

```bash
# macOS — produces a .app + .dmg under
# src-tauri/target/<triple>/release/bundle/
npm run release:mac

# Windows — produces a .msi + setup.exe
npm run release:win
```

Both are **unsigned** as of v0.1. To enable signing later:
- Mac: set `APPLE_CERTIFICATE`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_ID`,
  `APPLE_ID_PASSWORD`, `APPLE_TEAM_ID`; flip
  `bundle.macOS.signingIdentity` in `tauri.conf.json` to your Developer
  ID. Notarization happens automatically when `APPLE_ID` is set.
- Windows: set `TAURI_KEY_PASSWORD` for the bundled NSIS signer, and
  point `bundle.windows.certificateThumbprint` at your installed cert.

The unsigned build runs fine in dev — Mac shows a "developer can't be
verified" dialog on first launch (Cmd+click → Open works around it),
and Windows SmartScreen pops a similar warning that the user can
override. Both go away as soon as signing is configured.

## How the desktop client differs from web

The same SPA bundle ships to both deployments. Differences are gated
at runtime via:

- `PI_MODE=desktop` env var read by `web/backend/config.py:DEPLOY_MODE`.
- `window.__TAURI_INTERNALS__` runtime detection in
  `web/frontend/src/lib/native-bridge.ts:isDesktop()`.

| Feature | Web | Desktop |
|---|---|---|
| **Workspace storage** | sandboxed dir under `web/data/workspaces/<wsid>/` | the user's own folder, picked via OS dialog |
| **Workspace registration** | auto-created per chat | `Registry.register_desktop_workspace(path)` (no symlink wiring) |
| **Disk quota** | enforced (default 2 GB per workspace) | **disabled** — uses local disk |
| **Docker isolation** | every chat in `pi-session` container | subprocess only, in the user's folder |
| **Egress proxy** | MITM HTTPS for Vertex tokens | **skipped** (egress runs through user's network) |
| **Folder picker** | `window.prompt(...)` (web flow rarely uses this) | native `tauri-plugin-dialog` |
| **Sign in** | inline Clerk hosted page | external browser → `digi-setu://auth/callback` deep link |
| **Stripe Checkout** | full-page navigate to Stripe | external browser → `digi-setu://billing/return` deep link |
| **Permission mode default** | `approve_risky` (Cursor-style) | `approve_risky` (Cursor-style) |
| **Shadow git** | `web/data/shadows/<wsid>/` | OS app-data dir (e.g. `~/Library/Application Support/com.digisetu.desktop/data/shadows/`) |
| **pi CLI** | global npm install on the VM | bundled inside the .app/.exe |
| **Node.js** | system Node on the VM | bundled inside the .app/.exe |

## Data location

```
macOS    ~/Library/Application Support/com.digisetu.desktop/data/
Windows  %APPDATA%\com.digisetu.desktop\data\
Linux    ~/.local/share/com.digisetu.desktop/data/
```

This is exactly the pattern Cline uses for its shadow-git checkpoint
store (see `web/backend/services/shadow_git.py`'s header comment for
the full rationale of why shadows live here, not next to the user's
folder).

## Auth + billing wiring

The deep-link round-trip is documented in:

- `web/frontend/src/lib/desktop-auth.ts` — frontend handler
- `web/backend/routes/desktop_auth.py` — backend exchange endpoint

For end-to-end auth in production you must:

1. Add `digi-setu://auth/callback` to **Clerk dashboard → Authorized
   redirect URIs**.
2. Add `digi-setu` to **Allowed redirect schemes**.
3. Build the production `/desktop/sign-in?state=…&return=…` page on
   the web app — it must:
   - Render Clerk's SignIn component
   - On success, mint a single-use Clerk ticket via
     `users.createTicket()` (server-side)
   - `window.location = ${return}?token=${ticket}&state=${state}`
4. Wire the same flow for Stripe Checkout success/cancel URLs (the
   billing store already sends `digi-setu://billing/return` as
   `return_url` in desktop mode — see
   `desktop/frontend/src/stores/billing.ts`).

The `routes/desktop_auth.py:desktop_exchange` endpoint accepts the
ticket, calls Clerk to verify the resulting session, and stamps a
process-local desktop session for subsequent API calls.

## Troubleshooting

### "Sidecar binary missing"
Run `npm run sidecar:build`. The error message in `~/Library/Logs/com.digisetu.desktop/`
(Mac) or the dev console (Windows) lists the paths it tried.

### "vendor/pi/node_modules/.bin/pi missing"
Run `npm run pi-runtime:fetch` (this also installs pi). If it fails,
delete `pi-runtime/vendor/pi/` and re-run.

### "pi --version" hangs
Likely the bundled Node was downloaded for the wrong arch. Delete
`pi-runtime/vendor/node-<arch>/` and re-run `npm run pi-runtime:fetch
:current-platform-only`.

### Sidecar boots but the SPA shows "Loading…" forever
The sidecar's port wasn't announced to the SPA. Open the Tauri dev
tools (right-click → Inspect Element in dev), check the console for
`[boot] Desktop sidecar did not announce a port`. If you see that,
the sidecar likely crashed during boot — check the dev terminal for
PyInstaller errors.

### Clerk login: "redirect URI not allowed"
You haven't added `digi-setu://auth/callback` to the Clerk
dashboard's allowed redirect URIs. See *Auth + billing wiring* above.

### Mac: "Digi Setu can't be opened because Apple cannot check it for malicious software"
Expected on unsigned dev builds. Right-click the .app → Open → Open in
the warning dialog. Permanent fix: code signing (see *Release builds*).

### Windows: SmartScreen warning
Same — expected on unsigned builds. Click "More info" → "Run anyway".
Permanent fix: an EV code-signing certificate.

## What's NOT done yet

- **Auto-update** — Tauri has a built-in updater plugin we can wire up
  later. It needs a server-hosted update feed and a signing key, both
  of which are out of scope for v0.1.
- **Native menu bar** — Tauri uses the SPA's in-app header for now.
  Adding `tauri-plugin-menu` for "File / Edit / View / Help" menus is
  ~50 lines of Rust if/when needed.
- **Linux build** — the toolchain works (Tauri is Linux-first), but
  we don't ship .deb/.AppImage out of the box. Add the targets to
  `tauri.conf.json:bundle.targets` to enable.
- **Windows ARM** — only x64 is configured. Adding aarch64-pc-windows-
  msvc target is a one-line change once Microsoft's toolchain stops
  being a pain about it.

## See also

- `web/README.md` — the parent web app's docs
- `deploy/README.md` — production VM deploy notes (web mode)
- `web/backend/services/shadow_git.py` header — why shadows live in
  the OS app-data dir
- `web/frontend/src/views/Picker.vue` — the desktop workspace picker
  the user sees on first launch (mirrors Cursor's "Open project" UI
  pattern)
