# pi-typst-test · web (Step 1: chat parity)

Vue 3 chat UI driven by a Python FastAPI bridge that spawns `pi --mode rpc`
per session. Step 1 ships the chat column only — terminal pane, file tree,
and editor/diff come in Steps 2-4.

```
browser (Vue 3 + Pinia + Tailwind + markdown-it)
        │  WebSocket (forwards every JSONL event verbatim)
        ▼
FastAPI (web/backend/app.py)
        │  spawns: pi --mode rpc --provider anthropic-vertex \
        │              --model claude-opus-4-7 \
        │              --session-dir web/sessions/{id} \
        │              --extension ./extensions/typst-tools.ts
        ▼
pi (your patched anthropic-vertex provider, real Vertex creds via ADC)
```

Source-of-truth for the Vue components is
`pi-mono-main/packages/coding-agent/src/modes/interactive/`. Each component
header notes which TUI file it mirrors.

## One-time setup

```bash
# Backend
cd web/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

You also need pi installed globally (it already is — `pi --version` works)
and your patched anthropic-vertex provider applied (it already is —
`patches/apply.sh` was run).

## Running

Two terminals:

```bash
# Terminal A — backend
cd web/backend
source .venv/bin/activate
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

```bash
# Terminal B — frontend
cd web/frontend
npm run dev
```

Open http://localhost:5173. Click **+ New session**, type a prompt
(e.g. `List the 4 custom Typst tools, names only`), Cmd/Ctrl+Enter to send.
You should see streamed text + thinking + tool call cards, with token usage
chips per assistant turn.

Refresh the page → your session shows up under **Resume saved session**;
clicking it reattaches pi to that on-disk session and continues the
conversation.

## Layout

```
web/
├── backend/
│   ├── app.py              FastAPI + WebSocket bridge
│   ├── pi_session.py       subprocess wrapper (JSONL pump)
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json / vite.config.ts / tailwind.config.ts / tsconfig.json
│   └── src/
│       ├── main.ts
│       ├── app.css                     theme vars from dark.json
│       ├── App.vue                     session picker + active layout
│       ├── stores/session.ts           Pinia: WS + reduced ChatMessage[]
│       ├── lib/
│       │   ├── event-router.ts         RPC events → ChatMessage[]
│       │   ├── format.ts               formatTokens (port from footer.ts)
│       │   └── markdown.ts             markdown-it instance
│       ├── types/rpc.ts                RPC event types + render-ready types
│       └── components/
│           ├── StatusBar.vue           pi-tui FooterComponent equivalent
│           ├── MessageList.vue         scrollable column, sticky-bottom
│           ├── UserMessage.vue         user-message.ts mirror
│           ├── AssistantMessage.vue    assistant-message.ts mirror
│           ├── ThinkingBlock.vue       collapsible italic gray block
│           ├── ToolCallCard.vue        tool-execution.ts mirror (text-only Step 1)
│           ├── UsageChip.vue           per-message ↑in ↓out cR cW $cost
│           └── Composer.vue            textarea + Cmd/Ctrl+Enter send
└── sessions/                           created on first session, persisted JSONL
```

## What's NOT here yet (deferred)

| Feature | Step | Notes |
|---|---|---|
| Code editor pane (Monaco) | 2 | renders file when `read`/`edit` tool fires |
| Diff viewer | 2 | `monaco-diff-editor`, driven by `edit`/`write` tool args |
| Terminal pane (xterm.js) | 2 | reads `tool_execution_update` from `bash` |
| File tree | 3 | watches workspace + custom `peek_file` extension tool |
| File previews by type | 4 | image, PDF, etc. |
| Steer / followUp commands | 2 | `streamingBehavior: steer` while pi is responding |
| Multi-provider switcher | later | provider/model selector in StatusBar |
| Docker isolation | Phase 1 polish | separate Step once chat UX is locked |
| Auth, billing, quotas | Phase 1 polish | per-user enforcement |

## Notes / known limitations

- The backend reads provider/model from `scripts/env.sh` so it picks up your
  existing setup (anthropic-vertex / claude-opus-4-7 by default).
- Markdown rendering is intentionally minimal (no syntax highlighting yet).
  Code blocks render with a flat green color matching `mdCodeBlock`.
- Tool result rendering is generic text — Steps 2-4 introduce per-tool
  renderers (terminal, diff, file viewer) that will replace ToolCallCard's
  text fallback for `bash`, `edit`, `write`, `read`.
