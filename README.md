# pi-typst-test

A self-contained smoke-test harness that runs `pi-coding-agent` against the same Typst workflow your existing `typst-agent` covers, using the same Vertex ADC, the same Gemini model, and the same documentation corpus.

The point: stop arguing about ADK vs pi in the abstract. Run both against the same prompts, look at the logs, decide.

## What's in here

```
pi-typst-test/
├── package.json                     # registers extensions/typst-tools.ts
├── extensions/typst-tools.ts        # compile_typ, search_docs, list_fonts, list_packages
├── guides/                          # → symlink to ../refernecs/typst-agent/guides
├── workspace/                       # scratch dir for the agent
│   └── main.typ                     # starter document
├── .pi/APPEND_SYSTEM.md             # Typst persona appended to pi's defaults
├── AGENTS.md                        # short project context pi auto-loads
└── scripts/
    ├── env.sh                       # exports GOOGLE_CLOUD_* + model selection
    ├── install.sh                   # installs pi globally + npm i locally
    ├── run.sh                       # interactive (or one-shot if you pass a prompt)
    └── smoke.sh                     # 4 non-interactive prompts + pass/fail
```

## Quick start

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

scripts/install.sh
scripts/smoke.sh                     # ~3 min, prints PASS/FAIL summary
scripts/run.sh                       # interactive
```

For the full plan + concrete test prompts, see [RUN.md](./RUN.md).

## Desktop app

A Tauri-based macOS + Windows shell that wraps the same `web/` codebase
lives under [`desktop/`](./desktop/). It bundles the FastAPI backend
(via PyInstaller), Node.js, and pi-coding-agent into a single drag-to-
Applications install. See [`desktop/README.md`](./desktop/README.md) for
the full dev loop, release scripts, and how the desktop client differs
from the hosted web product.

## What this exists to test

1. Does pi load a 4-tool extension correctly via `package.json`'s `pi.extensions` field?
2. Does Vertex ADC work end-to-end (main agent + Flash-Lite responder for `search_docs`)?
3. Does the compile-loop pattern (`write → compile_typ → fix → re-compile`) work as well as ADK's?
4. Does pi's built-in compaction + sessions hold up across the kind of session your typst-agent regularly handles?
5. How dense / hallucination-free are pi's outputs on Touying / CeTZ / Fletcher compared to your current agent?

The honest answer to "should I drop ADK?" lives in those five answers. Run the smoke test, run the six interactive prompts in `RUN.md`, then we can talk.
