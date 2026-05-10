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

# Auth SDKs use lazy / codegen'd imports. (No `stripe` here — the
# desktop has zero billing code; Stripe lives only on the cloud.)
hiddenimports += collect_submodules("clerk_backend_api")
hiddenimports += collect_submodules("svix")

# Crypto + Google auth (used by services/egress_proxy.py — desktop
# doesn't run that proxy but importing app loads the module).
hiddenimports += collect_submodules("cryptography")
hiddenimports += collect_submodules("google.auth")

# markitdown + format-specific parser deps for the office-preview / read-
# binary path in services/binary_extract.py. markitdown does dynamic
# imports at convert time depending on the file's extension, so we have
# to enumerate every parser ourselves; PyInstaller's static analysis
# misses them and the frozen binary falls back to "library not installed"
# placeholders for that file type. Wrapped in try/except because not
# every parser is present in every dev environment.
for _md_pkg in (
    "markitdown",
    "pdfminer",
    "pdfminer.six",
    "pypdf",
    "docx",                    # python-docx
    "openpyxl",
    "xlrd",
    "pptx",                    # python-pptx
    "mammoth",
    "olefile",
    "pandas",                  # markitdown uses pandas for some xlsx paths
    "beautifulsoup4",
    "bs4",
    "lxml",
    "markdownify",
    "magika",                  # mime sniffing
    "charset_normalizer",
    "extract_msg",             # outlook .msg
    "pydub",                   # tolerated even without audio extra
):
    try:
        hiddenimports += collect_submodules(_md_pkg)
    except Exception:
        pass


# ── data files (templates, configs, etc) ──────────────────────────────
# `web/backend/fonts` is a static asset directory the routes/files.py
# endpoints read on startup. We bundle the whole tree so the frozen
# binary self-contains its assets.
#
# IMPORTANT: this list MUST be initialised before the markitdown
# `collect_data_files` block below — that block uses ``datas += …`` and
# until 2026-05 it lived above this line, NameError'ing into a
# silently-swallowed try/except so markitdown's parser-registry data
# files never made it into the bundle. Symptom: frozen sidecar
# imports markitdown OK but fails at convert time on certain formats.
datas = []
fonts_dir = os.path.join(BACKEND_DIR, "fonts")
if os.path.isdir(fonts_dir):
    datas.append((fonts_dir, "fonts"))

# markitdown ships a converter registry as data files (extension → parser
# class plug-in points). collect_data_files makes sure those land in the
# bundle alongside the python code. pdfminer + pypdf carry their own
# resource tables (cmap data, ToUnicode mappings) we MUST bundle for
# scanned-PDF text extraction to work in the frozen binary.
from PyInstaller.utils.hooks import collect_data_files as _collect_data_files
for _data_pkg in (
    "markitdown",
    "pdfminer",
    "pypdf",
    "docx",
    "pptx",
    "openpyxl",
    "mammoth",
):
    try:
        datas += _collect_data_files(_data_pkg)
    except Exception:
        pass

# Ship desktop/backend/.pi/APPEND_SYSTEM.md so pi_session.py can read
# it at spawn time and pass it via --append-system-prompt. The file
# encodes desktop-mode behaviour (no container, workspace boundary,
# protected-paths list) and must follow the binary, not the user's
# checkout. PyInstaller stages it under <_MEIPASS>/.pi/ at runtime.
pi_md = os.path.join(BACKEND_DIR, ".pi", "APPEND_SYSTEM.md")
if os.path.isfile(pi_md):
    datas.append((pi_md, ".pi"))

# Third-party software notices file. Generated by
# desktop/scripts/gen-third-party-licenses.mjs as part of release
# builds (build-mac.sh / build-windows.ps1 invoke it). Bundling it
# inside the sidecar lets the SPA serve it through a backend route
# regardless of where Tauri places its own resources directory.
licenses_txt = os.path.join(DESKTOP_ROOT, "THIRD_PARTY_LICENSES.txt")
if os.path.isfile(licenses_txt):
    datas.append((licenses_txt, "."))

# Pull in all data files for packages that ship templates / certs.
for pkg in ("certifi", "clerk_backend_api", "svix"):
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
