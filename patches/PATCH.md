# `anthropic-vertex` provider patch for `pi`

Adds **Anthropic Claude on Vertex AI** as a first-class provider in `pi`,
mirroring the existing `google-vertex` pattern: same project + ADC auth, just
routed to Anthropic's models in Model Garden instead of Google's Gemini.

After this patch you can do:

```bash
unset ANTHROPIC_API_KEY                         # we use ADC, not the API
export GOOGLE_CLOUD_PROJECT=frontend-472812
export GOOGLE_CLOUD_LOCATION=global             # opus-4-7 GA region

pi --provider anthropic-vertex --model claude-opus-4-7 -p "say OK"
```

…and pi will negotiate gcloud Application Default Credentials, hit
`https://aiplatform.googleapis.com/v1/projects/.../publishers/anthropic/models/claude-opus-4-7:streamRawPredict`,
and stream Claude tokens through pi's normal agent loop (tools, sessions,
extensions, everything).

Tested with `claude-opus-4-7` on `frontend-472812`, region `global`. Same
Codly prompt that took the Gemini agent **233.8s / ~33 turns** finishes in
**24.2s / 2 turns** with Opus.

---

## What's actually patched

Everything lives under the user's global `pi` install:

```
$(npm root -g)/@mariozechner/pi-coding-agent/
├── dist/core/provider-display-names.js          (1 line)
├── dist/core/model-resolver.js                  (1 line)
└── node_modules/
    ├── @anthropic-ai/vertex-sdk/                (NEW dependency)
    └── @mariozechner/pi-ai/dist/
        ├── env-api-keys.js                      (~15 lines: ADC branch)
        ├── models.generated.js                  (~50 lines: 3 model entries)
        └── providers/
            ├── anthropic.js                     (2 helpers: now exported)
            ├── anthropic-vertex.js              (NEW file ~80 lines)
            └── register-builtins.js             (~25 lines: lazy + register)
```

### Architectural decision: delegation over duplication

`anthropic-vertex.js` is a thin wrapper. It does just two things:

1. Build an `AnthropicVertex` client (which carries `google-auth-library` for ADC).
2. Delegate to `anthropic.js`'s existing `streamAnthropic` by passing the
   client through `options.client` (the regular Anthropic provider already
   accepts a pre-built client there — line ~299 of anthropic.js).

The only minor wrinkle: pi-coding-agent's session loop calls `streamSimple`,
not `stream`. `streamSimpleAnthropic` rebuilds options through
`buildBaseOptions()` which **strips `client`** and **requires an apiKey**, so
we can't just delegate; we replicate its tiny adaptive-thinking dispatch in
our own `streamSimpleAnthropicVertex` and skip those two checks.

### Why a separate `api: "anthropic-vertex"` instead of branching `anthropic-messages`?

Cleaner dispatch. The api-registry (`api-registry.js`) keys providers on
`model.api`, and a separate api type keeps the Vertex routing isolated from
the direct-Anthropic codepath. It also matches how `google-vertex` and
`google-generative-ai` are split — sibling providers that share the
underlying SDK shape but have distinct auth/endpoint stories.

---

## Reapplying after `pi update`

`pi update` will reinstall `pi-coding-agent` and wipe everything in
`node_modules`. To restore the patch:

```bash
bash patches/apply.sh
```

`apply.sh` is idempotent — runs the SDK install (skipped if present), drops
the new provider file, then re-runs each StrReplace via Node (skipped if the
target string is already in the file).

Backups of every modified file (pre-patch) live in `patches/backups/`. To
revert manually, `cp` them back to their original locations.

---

## Env vars

| Variable                          | Purpose                                                                  | Default              |
|-----------------------------------|--------------------------------------------------------------------------|----------------------|
| `GOOGLE_CLOUD_PROJECT`            | GCP project (must have Anthropic enabled in Model Garden)                | required             |
| `GOOGLE_CLOUD_LOCATION`           | Vertex region                                                            | `global`             |
| `PI_VERTEX_ANTHROPIC_PROJECT`     | Override project just for anthropic-vertex                               | falls back to above  |
| `PI_VERTEX_ANTHROPIC_LOCATION`    | Override region just for anthropic-vertex                                | falls back to above  |
| `PI_VERTEX_ANTHROPIC_DEBUG`       | When set, logs `[lazy-streamSimple]` + `[anthropic-vertex]` to stderr    | unset (silent)       |

`scripts/env.sh` auto-pins `PI_VERTEX_ANTHROPIC_LOCATION=global` when
`PI_PROVIDER=anthropic-vertex`, because that's where claude-opus-4-7 is GA
today (other regions return 403).

---

## Available models

| Model               | Context | Max out | Cost in/out (per 1M tok) |
|---------------------|--------:|--------:|--------------------------|
| `claude-opus-4-7`   |   1M    |   128K  | $15 / $75                |
| `claude-opus-4-6`   |   200K  |    64K  | $15 / $75                |
| `claude-opus-4-5`   |   200K  |    64K  | $5  / $25                |
| `claude-sonnet-4-6` |   200K  |    64K  | $3  / $15                |

To add Sonnet 4.6 etc., add another entry to the `"anthropic-vertex"` block
in `models.generated.js` (and to `apply-edits.mjs` so the patch script
re-adds it on the next reapply).

---

## Smoke test

```bash
unset ANTHROPIC_API_KEY ANTHROPIC_OAUTH_TOKEN
source scripts/env.sh
PI_PROVIDER=anthropic-vertex PI_MODEL=claude-opus-4-7 \
  pi --provider $PI_PROVIDER --model $PI_MODEL -p "reply with exactly: OK"
```

To diff the two brains on the same Codly prompt:

```bash
# Gemini (default)
source scripts/env.sh
python3 scripts/rpc_driver.py "$CODLY_PROMPT"

# Opus 4.7 on Vertex
source scripts/env.sh
PI_PROVIDER=anthropic-vertex PI_MODEL=claude-opus-4-7 \
  python3 scripts/rpc_driver.py "$CODLY_PROMPT"
```
