# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the Digi Setu desktop sidecar.

Run with:
    pyinstaller --clean --noconfirm desktop/sidecar/pyinstaller.spec

Output:
    desktop/sidecar/dist/pi-typst-sidecar(.exe)        — single file
    desktop/sidecar/dist/pi-typst-sidecar-<triple>     — Tauri-compatible
                                                         platform-suffix copy

The spec is platform-aware so the same file works on Mac, Linux and
Windows; we just rename the output afterward in build_sidecar.{sh,ps1}.

Why a single-file binary:
    - Tauri's `bundle.externalBin` expects one file per platform.
    - Easier to ship; fewer DLL/dylib path issues at runtime.
    - Cold-start cost (~1-2s for the bootloader to extract)
      acceptable for a desktop app.

Tricky packages and how we handle them:
    - uvicorn[standard]    : pulls uvloop / httptools / watchfiles etc.
                             Use `--collect-all` so every submodule is
                             included.
    - websockets           : pure-python but PyInstaller misses some
                             internal imports.
    - watchdog             : platform-specific backends (FSEvents on
                             Mac, ReadDirectoryChangesW on Win).
    - clerk-backend-api    : codegen'd; collect-all to be safe.
    - svix                 : webhook signature lib; pure-python.
    - stripe               : has lazy resource imports; collect-all.
    - cryptography         : native (libssl). PyInstaller's hooks pick
                             it up but pin them explicitly.
"""

import os
import sys
import platform
from PyInstaller.utils.hooks import collect_submodules, collect_all

block_cipher = None

HERE = os.path.dirname(os.path.abspath(SPEC))
DESKTOP_ROOT = os.path.abspath(os.path.join(HERE, ".."))
# Desktop has its own backend fork at desktop/backend/. The web
# backend at the repo root stays untouched. Switching this single
# constant is the only thing that decides which tree gets frozen.
BACKEND_DIR = os.path.join(DESKTOP_ROOT, "backend")

# ── extra paths PyInstaller scans for imports ─────────────────────────
extra_pathex = [BACKEND_DIR]


# ── hidden imports that PyInstaller's static analysis misses ──────────
# Most of these come from collect_all(); the explicit list is for
# packages whose import chains are dynamic.
hiddenimports = []
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("uvicorn.lifespan")
hiddenimports += collect_submodules("uvicorn.protocols")
hiddenimports += collect_submodules("uvicorn.loops")
hiddenimports += collect_submodules("websockets")
hiddenimports += collect_submodules("watchdog")
hiddenimports += collect_submodules("watchdog.observers")
hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("starlette")
hiddenimports += collect_submodules("pydantic")
hiddenimports += collect_submodules("pydantic_core")
hiddenimports += [
    "h11",
    "httptools",
    "python_multipart",
    "multipart",
    "anyio",
    "sniffio",
    "click",
    "email.mime.text",
    "email.mime.multipart",
]

# Auth + billing SDKs use lazy / codegen'd imports.
hiddenimports += collect_submodules("clerk_backend_api")
hiddenimports += collect_submodules("svix")
hiddenimports += collect_submodules("stripe")

# Crypto + Google auth (used by services/egress_proxy.py — desktop
# doesn't run that proxy but importing app loads the module).
hiddenimports += collect_submodules("cryptography")
hiddenimports += collect_submodules("google.auth")


# ── data files (templates, configs, etc) ──────────────────────────────
# `web/backend/fonts` is a static asset directory the routes/files.py
# endpoints read on startup. We bundle the whole tree so the frozen
# binary self-contains its assets.
datas = []
fonts_dir = os.path.join(BACKEND_DIR, "fonts")
if os.path.isdir(fonts_dir):
    datas.append((fonts_dir, "fonts"))

# Pull in all data files for packages that ship templates / certs.
for pkg in ("certifi", "stripe", "clerk_backend_api", "svix"):
    try:
        from PyInstaller.utils.hooks import collect_data_files
        datas += collect_data_files(pkg)
    except Exception:
        pass


# ── platform-specific tweaks ──────────────────────────────────────────
# uvloop is unix-only; on Windows the import would fail at boot, so
# we exclude it. uvicorn's auto-detection then falls back to asyncio.
excludes = []
if sys.platform == "win32":
    excludes += ["uvloop"]


a = Analysis(
    [os.path.join(HERE, "sidecar_main.py")],
    pathex=extra_pathex,
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="pi-typst-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,        # UPX breaks some signed binaries on Mac/Win
    runtime_tmpdir=None,
    console=True,     # Backend logs go to stderr; Tauri pumps them
    disable_windowed_traceback=False,
    icon=None,
)
