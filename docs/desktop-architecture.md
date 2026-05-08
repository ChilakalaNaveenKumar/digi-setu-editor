# Desktop architecture — Cursor-style hybrid

**Status:** approved 2026-05-08, M1 in progress.
**Last revised:** 2026-05-08
**Owner:** Naveen (architect) + Claude (implementing).

This document is the source of truth for how the Digi Setu desktop app
authenticates AI calls, where prompts/tokens flow, and which subset of
the codebase lives where. It supersedes any chat-thread decisions; if
the doc and a chat thread disagree, the doc wins.

---

## 1. The problem we are solving

The hosted (`web/`) deployment talks to Vertex AI via the operator's
`GOOGLE_APPLICATION_CREDENTIALS` service-account JSON, brokered through
`services/egress_proxy.py` (TLS MITM that injects a fresh Vertex bearer
token). That posture is safe **only because the credential never leaves
the operator's server.**

The desktop fork inherits the same backend code but runs on the user's
laptop. We **cannot** copy the operator's service-account JSON into the
binary — anyone who downloads the app could `unzip` the build and use
the operator's Vertex quota for free. So the desktop must obtain AI
access by some other means.

## 2. Architecture (Cursor pattern)

Three branches, decided per chat session at WebSocket open:

```
                  ┌─ has BYOK key for picked model? ──→  LOCAL pi
                  │                                       (today's BYOK
                  │                                        path; user
                  │                                        pays provider)
desktop chat WS ──┤
                  │                                      ┌─ paid plan?
                  │                                      │  ──→ CLOUD RELAY
                  │                                      │     to api.digi-setu.com
                  └─ no BYOK key? ──→ Clerk signed in? ──┤     (operator pays
                                                          │      Vertex, user
                                                          │      pays subscription)
                                                          │
                                                          └─ free / no plan
                                                            ──→ "Upgrade or BYOK" modal

                       ──→ not signed in?
                           ──→ "Sign in or add a key" modal
                              (no_chat_no_login rule)
```

Each branch is **independently shippable** — we get value from M1
(operator stays unblocked) before any of M2–M5 land.

## 3. What lives where

| Concern | Lives in | Notes |
|---|---|---|
| Hosted web SPA + REST + cloud chat | `web/backend`, `web/frontend` | Stays on `digi-setu.com`. Already shipped. |
| Cloud relay endpoint (NEW) | `web/backend/routes/desktop_relay.py` | New file. Sister of `chat_ws.py`. Reuses `pi_session.py` + `egress_proxy.py`. |
| Desktop sidecar binary | `desktop/backend` (PyInstaller) | Local registry, BYOK routing, file-system access, chat WS dispatcher. |
| Desktop UI shell | `desktop/frontend` (Vue 3 + Tauri) | Identical SPA to web; just the chat WS URL differs at runtime. |
| Tauri shell | `desktop/src-tauri` | OS integration, deep-link, single-instance, sidecar lifecycle. |

## 4. Endpoint scheme: `api.digi-setu.com/v1/...`

| Concern | Endpoint | Notes |
|---|---|---|
| Marketing + web SPA | `digi-setu.com` | Existing |
| Web SPA WS (chat) | `wss://digi-setu.com/ws/sessions/{sid}` | Existing |
| Web SPA REST | `https://digi-setu.com/api/...` | Existing |
| Desktop relay WS (NEW) | `wss://api.digi-setu.com/v1/ws/desktop-relay` | New Caddy block. Same backend (`127.0.0.1:8788`) for v1; can split to its own VM/Cloud Run later without changing client URLs. |
| Desktop relay health | `https://api.digi-setu.com/v1/health` | Smoke probe before wiring relay. |

**Why a separate subdomain instead of `digi-setu.com/api/v1/desktop-relay`?**
- Industry convention (Cursor uses `api2.cursor.sh`, Stripe uses
  `api.stripe.com`, etc.).
- Lets us version (`/v1`) so a desktop binary shipped today keeps working
  when we add `/v2` later.
- Different Caddy block means we can apply different CORS / WS origin
  rules to the relay than the web SPA.
- Same Cloudflare zone, same Caddy instance, **trivial ops cost.**

## 5. BYOK probe — what counts as "user has a key"

Today (`config.py`):
```python
_BYOK_PROBE_VARS = (
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",  # ← problem
    "OPENAI_API_KEY",
)
```

`GOOGLE_APPLICATION_CREDENTIALS` is operator-shaped. End users virtually
never have one — their "Google key" is a 40-character `GEMINI_API_KEY`
from AI Studio. Treating ADC JSON as BYOK accidentally pushed the
operator's local laptop into BYOK mode and routed Gemini through the
Vertex provider, which hangs without a project.

**Decision (M1):** drop `GOOGLE_APPLICATION_CREDENTIALS` from the BYOK
probe. Treat it as **operator-only** behind a separate gate
`PI_OPERATOR_VERTEX=1`. End users get the cleaner story:

| User state | Mode | Reason |
|---|---|---|
| Has `ANTHROPIC_API_KEY` | BYOK Anthropic direct | Real end-user key |
| Has `GEMINI_API_KEY` / `GOOGLE_API_KEY` | BYOK AI Studio direct | Real end-user key |
| Has `OPENAI_API_KEY` | BYOK OpenAI direct | Real end-user key |
| Has only `GOOGLE_APPLICATION_CREDENTIALS` | NOT BYOK | Operator artefact; falls through to Clerk relay |
| Has `GOOGLE_APPLICATION_CREDENTIALS` AND `PI_OPERATOR_VERTEX=1` | BYOK Vertex (operator dev) | Naveen's local self-test |

## 6. Relay protocol (preview — finalised in M2)

Same JSON message schema as today's local chat WS. The frontend
renders identically; only the hop differs.

```
client → server :  { "type": "session_init", "model": "...", "permission_mode": "..." }
client → server :  { "type": "user_message", "content": "...", "attachments": [...] }
server → client :  { "type": "delta", "text": "..." }
server → client :  { "type": "tool_call", "id": "...", "tool": "read_file", "args": {"path": "..."} }
client → server :  { "type": "tool_result", "id": "...", "ok": true, "content": "..." }
server → client :  { "type": "permission_request", ... }
client → server :  { "type": "permission_response", ... }
server → client :  { "type": "message_end", "usage": { "input_tokens": ..., "output_tokens": ... } }
```

**Tool calls always round-trip to the desktop** — the user's full
codebase NEVER ships to api.digi-setu.com. Only the bytes the model
explicitly requests, and (with `approve_risky` approval) the bytes
the model writes. This matches Cursor's design exactly.

**Auth:** Clerk session JWT in `Sec-WebSocket-Protocol: bearer.<token>`
(only header browsers allow on `new WebSocket(...)`).

**Stripe gate:** every relay session checks the user's plan; free plan
has a per-day token cap, paid plans use overage metering via
`stripe.SubscriptionItem.create_usage_record`.

## 7. Security posture

| Threat | Mitigation |
|---|---|
| User extracts Vertex creds from binary | Impossible — only `api.digi-setu.com` URL ships. |
| User abuses operator's Vertex quota | Clerk JWT verified per-message, Stripe plan + per-user rate limit. |
| User exfiltrates other users' chats | Relay enforces `user_id` ownership on every workspace/session lookup (existing `registry.py` pattern). |
| Operator backend RCE | Existing `egress_proxy.py` MITM design contains the blast radius — Vertex token never enters per-session containers. |
| Desktop binary tampered to call evil relay | `PI_RELAY_BASE` is a runtime env override. Default is hard-coded to prod. A re-signed binary could redirect — but that's a problem for every BYOK app and out of scope for v1 (covered by code-signing in v2). |
| User's prompts leak to operator (privacy) | **Documented explicitly in privacy policy.** BYOK users opt out by adding their own key. Cloud-relay users explicitly accept this in the sign-in flow. |

## 8. Build order (each milestone is independently shippable)

| ID | Scope | Eta | Blocks |
|---|---|---|---|
| M0 | This doc | – | nothing |
| M1 | BYOK probe tightening + `PI_OPERATOR_VERTEX=1` | today | M3 |
| M2 | `web/backend/routes/desktop_relay.py` scaffold + Caddyfile `api.digi-setu.com` block + `/v1/health` | 1 day | M3 |
| M3 | Desktop dispatcher: BYOK / relay / sign-in branches in `desktop/backend/routes/chat_ws.py` + `PI_RELAY_BASE` config | 1 day | M4 |
| M4 | Tool brokering over relay (`tool_call` ↔ `tool_result` round-trip) | 2 days | M5 |
| M5 | Stripe usage metering on relay messages | 1 day | M6 |
| M6 | Model picker badges (BYOK / CLOUD / Sign-in / Upgrade) + settings toggle | 1 day | M7 |
| M7 | Activity dashboard dual-source (cloud USD/tokens + local tokens-only) | 0.5 day | – |

Total: ~7–8 focused days for the full Cursor-style desktop.

## 9. Things explicitly OUT of scope

- Local model inference (no laptop runs Sonnet). If users want local
  models they can BYOK Ollama / LM Studio later (separate feature).
- Enterprise SSO (Okta, etc.) — Clerk handles SSO at a separate price
  point; not v1.
- Customer-managed Vertex (BYOC). Eventually a BYOK Vertex tier with
  the customer's own GOOGLE_APPLICATION_CREDENTIALS, but that's M8+.
- Code signing / notarisation (separate ops work, not architecture).
- Auto-update / Squirrel-style updaters — `tauri-updater` is a separate
  feature, not part of this design.

## 10. Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-08 | Adopt Cursor-style hybrid (Option C) | Matches `cloud_relay` chosen earlier; reuses `egress_proxy.py` and `container_pool.py` already built. |
| 2026-05-08 | `api.digi-setu.com` subdomain (not `/api/v1/` path) | Industry convention; allows independent scaling later; trivial ops cost via existing Cloudflare DNS-01. |
| 2026-05-08 | JSON-RPC tool brokering on the same chat WS | One channel = simpler ops. Cursor uses the same pattern. User confirmed: "API call just calls Claude, that's it." |
| 2026-05-08 | Drop `GOOGLE_APPLICATION_CREDENTIALS` from BYOK probe | It's operator-shaped, not user-shaped. End users have `GEMINI_API_KEY`. |
| 2026-05-08 | Add `PI_OPERATOR_VERTEX=1` override | Operator (Naveen) needs to keep self-testing locally with the service-account JSON. |
