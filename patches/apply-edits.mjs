#!/usr/bin/env node
// patches/apply-edits.mjs — idempotent in-place patches for pi-coding-agent
// + pi-ai. Called by apply.sh.
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const PI_PKG = process.argv[2];
// Optional 2nd arg from apply.sh — the resolved pi-ai location
// (handles the nested vs hoisted npm layout). Fall back to the
// nested path for backwards compat with older callers / dev usage.
const PI_AI = process.argv[3] ?? join(PI_PKG, "node_modules", "@mariozechner", "pi-ai");
if (!PI_PKG) {
  console.error("usage: node apply-edits.mjs <pi-coding-agent-dir> [pi-ai-dir]");
  process.exit(1);
}

function patch(file, find, replace, label, sentinel) {
  const src = readFileSync(file, "utf8");
  // Sentinel lets callers signal "already patched" with a short unique string,
  // which is more reliable than matching whitespace-sensitive multi-line blocks.
  if (sentinel && src.includes(sentinel)) {
    console.log(`✓ already patched : ${label}`);
    return;
  }
  if (src.includes(replace)) {
    console.log(`✓ already patched : ${label}`);
    return;
  }
  if (!src.includes(find)) {
    console.error(`✗ skip (anchor not found) : ${label}`);
    console.error(`  in ${file}`);
    return;
  }
  writeFileSync(file, src.replace(find, replace));
  console.log(`✓ patched         : ${label}`);
}

// ── 1. register-builtins.js: add lazy loader + register api ──────────────
{
  const f = join(PI_AI, "dist/providers/register-builtins.js");
  patch(
    f,
    `let anthropicProviderModulePromise;
let azureOpenAIResponsesProviderModulePromise;`,
    `let anthropicProviderModulePromise;
let anthropicVertexProviderModulePromise;
let azureOpenAIResponsesProviderModulePromise;`,
    "register-builtins: declare anthropicVertexProviderModulePromise",
  );
  patch(
    f,
    `function loadAnthropicProviderModule() {
    anthropicProviderModulePromise ||= import("./anthropic.js").then((module) => {
        const provider = module;
        return {
            stream: provider.streamAnthropic,
            streamSimple: provider.streamSimpleAnthropic,
        };
    });
    return anthropicProviderModulePromise;
}`,
    `function loadAnthropicProviderModule() {
    anthropicProviderModulePromise ||= import("./anthropic.js").then((module) => {
        const provider = module;
        return {
            stream: provider.streamAnthropic,
            streamSimple: provider.streamSimpleAnthropic,
        };
    });
    return anthropicProviderModulePromise;
}
function loadAnthropicVertexProviderModule() {
    anthropicVertexProviderModulePromise ||= import("./anthropic-vertex.js").then((module) => {
        const provider = module;
        return {
            stream: provider.streamAnthropicVertex,
            streamSimple: provider.streamSimpleAnthropicVertex,
        };
    });
    return anthropicVertexProviderModulePromise;
}`,
    "register-builtins: define loadAnthropicVertexProviderModule",
  );
  patch(
    f,
    `export const streamAnthropic = createLazyStream(loadAnthropicProviderModule);
export const streamSimpleAnthropic = createLazySimpleStream(loadAnthropicProviderModule);`,
    `export const streamAnthropic = createLazyStream(loadAnthropicProviderModule);
export const streamSimpleAnthropic = createLazySimpleStream(loadAnthropicProviderModule);
export const streamAnthropicVertex = createLazyStream(loadAnthropicVertexProviderModule);
export const streamSimpleAnthropicVertex = createLazySimpleStream(loadAnthropicVertexProviderModule);`,
    "register-builtins: export lazy streams",
  );
  patch(
    f,
    `    registerApiProvider({
        api: "anthropic-messages",
        stream: streamAnthropic,
        streamSimple: streamSimpleAnthropic,
    });`,
    `    registerApiProvider({
        api: "anthropic-messages",
        stream: streamAnthropic,
        streamSimple: streamSimpleAnthropic,
    });
    registerApiProvider({
        api: "anthropic-vertex",
        stream: streamAnthropicVertex,
        streamSimple: streamSimpleAnthropicVertex,
    });`,
    "register-builtins: registerApiProvider anthropic-vertex",
  );
}

// ── 2. anthropic.js: export two private helpers we reuse ─────────────────
{
  const f = join(PI_AI, "dist/providers/anthropic.js");
  patch(
    f,
    "function supportsAdaptiveThinking(modelId) {",
    "// Patched: exported for reuse by anthropic-vertex.js\nexport function supportsAdaptiveThinking(modelId) {",
    "anthropic.js: export supportsAdaptiveThinking",
  );
  patch(
    f,
    "function mapThinkingLevelToEffort(model, level) {",
    "// Patched: exported for reuse by anthropic-vertex.js\nexport function mapThinkingLevelToEffort(model, level) {",
    "anthropic.js: export mapThinkingLevelToEffort",
  );
}

// ── 3. env-api-keys.js: recognize ADC for anthropic-vertex ───────────────
{
  const f = join(PI_AI, "dist/env-api-keys.js");
  patch(
    f,
    `        if (hasCredentials && hasProject && hasLocation) {
            return "<authenticated>";
        }
    }`,
    `        if (hasCredentials && hasProject && hasLocation) {
            return "<authenticated>";
        }
    }
    // Anthropic on Vertex: same ADC mechanism as google-vertex (location defaults to "global"
    // if unset, since most Anthropic-on-Vertex models live there). Patched in.
    if (provider === "anthropic-vertex") {
        const hasCredentials = hasVertexAdcCredentials();
        const hasProject = !!(process.env.GOOGLE_CLOUD_PROJECT ||
            process.env.GCLOUD_PROJECT ||
            process.env.PI_VERTEX_ANTHROPIC_PROJECT ||
            getProcEnv("GOOGLE_CLOUD_PROJECT") ||
            getProcEnv("GCLOUD_PROJECT"));
        if (hasCredentials && hasProject) {
            return "<authenticated>";
        }
    }`,
    "env-api-keys: anthropic-vertex ADC branch",
  );
  // ── 3b. Trust the GCE metadata server when no ADC file is present ─────
  //
  // Inside the dual-uid sandbox container running on a GCE VM, neither
  // GOOGLE_APPLICATION_CREDENTIALS nor ~/.config/gcloud/application_default_credentials.json
  // exists — but http://metadata.google.internal IS reachable and the
  // attached service account has roles/aiplatform.user. The actual
  // google-auth-library inside the Vertex / Anthropic-Vertex SDKs will
  // happily fetch a token from metadata at request time.
  //
  // pi-ai's auth-presence heuristic, however, only checks for an ADC
  // FILE on disk and rejects the chat at startup with "No API key
  // found" before the SDK ever gets a chance to try metadata. Patch
  // hasVertexAdcCredentials so it ALSO returns true when the operator
  // explicitly opts in via `PI_TRUST_GCE_METADATA=1` (set by
  // services/pi_session.py on the GCE VM). We don't auto-detect by
  // probing 169.254.169.254 because the probe is sync-only here and we
  // don't want to add a network round-trip to every getEnvApiKey()
  // call.
  patch(
    f,
    `function hasVertexAdcCredentials() {
    if (cachedVertexAdcCredentialsExists === null) {`,
    `function hasVertexAdcCredentials() {
    // Operator-opt-in: on GCE / Cloud Run with workload identity, the
    // ADC file is absent but the metadata server provides tokens at
    // request time. See patches/apply-edits.mjs §3b.
    if (process.env.PI_TRUST_GCE_METADATA === "1") {
        return true;
    }
    if (cachedVertexAdcCredentialsExists === null) {`,
    "env-api-keys: hasVertexAdcCredentials trusts PI_TRUST_GCE_METADATA",
  );
}

// ── 4. models.generated.js: register the three models ────────────────────
{
  const f = join(PI_AI, "dist/models.generated.js");
  patch(
    f,
    `            contextWindow: 1000000,
            maxTokens: 64000,
        },
    },
    "azure-openai-responses": {`,
    `            contextWindow: 1000000,
            maxTokens: 64000,
        },
    },
    "anthropic-vertex": {
        "claude-opus-4-7": {
            id: "claude-opus-4-7",
            name: "Claude Opus 4.7 (Vertex)",
            api: "anthropic-vertex",
            provider: "anthropic-vertex",
            baseUrl: "https://aiplatform.googleapis.com",
            reasoning: true,
            input: ["text", "image"],
            cost: { input: 15, output: 75, cacheRead: 1.5, cacheWrite: 18.75 },
            contextWindow: 1000000,
            maxTokens: 128000,
        },
        "claude-opus-4-6": {
            id: "claude-opus-4-6",
            name: "Claude Opus 4.6 (Vertex)",
            api: "anthropic-vertex",
            provider: "anthropic-vertex",
            baseUrl: "https://aiplatform.googleapis.com",
            reasoning: true,
            input: ["text", "image"],
            cost: { input: 15, output: 75, cacheRead: 1.5, cacheWrite: 18.75 },
            contextWindow: 200000,
            maxTokens: 64000,
        },
        "claude-opus-4-5": {
            id: "claude-opus-4-5",
            name: "Claude Opus 4.5 (Vertex)",
            api: "anthropic-vertex",
            provider: "anthropic-vertex",
            baseUrl: "https://aiplatform.googleapis.com",
            reasoning: true,
            input: ["text", "image"],
            cost: { input: 5, output: 25, cacheRead: 0.5, cacheWrite: 6.25 },
            contextWindow: 200000,
            maxTokens: 64000,
        },
        "claude-sonnet-4-6": {
            id: "claude-sonnet-4-6",
            name: "Claude Sonnet 4.6 (Vertex)",
            api: "anthropic-vertex",
            provider: "anthropic-vertex",
            baseUrl: "https://aiplatform.googleapis.com",
            reasoning: true,
            input: ["text", "image"],
            cost: { input: 3, output: 15, cacheRead: 0.3, cacheWrite: 3.75 },
            contextWindow: 200000,
            maxTokens: 64000,
        },
    },
    "azure-openai-responses": {`,
    "models.generated: anthropic-vertex group",
    `"anthropic-vertex": {`,
  );
  // ── 4b. Incremental: add Claude Haiku 4.5 to the anthropic-vertex
  //         group on already-patched installs. The original §4 patch
  //         shipped without Haiku; this rider adds it without
  //         requiring a fresh `npm install`. Sentinel is the
  //         "(Vertex)" display name which is unique to our patched
  //         entry — it deliberately doesn't collide with the same
  //         model id in anthropic-direct / bedrock / cloudflare.
  patch(
    f,
    `        "claude-sonnet-4-6": {
            id: "claude-sonnet-4-6",
            name: "Claude Sonnet 4.6 (Vertex)",
            api: "anthropic-vertex",
            provider: "anthropic-vertex",
            baseUrl: "https://aiplatform.googleapis.com",
            reasoning: true,
            input: ["text", "image"],
            cost: { input: 3, output: 15, cacheRead: 0.3, cacheWrite: 3.75 },
            contextWindow: 200000,
            maxTokens: 64000,
        },
    },
    "azure-openai-responses": {`,
    `        "claude-sonnet-4-6": {
            id: "claude-sonnet-4-6",
            name: "Claude Sonnet 4.6 (Vertex)",
            api: "anthropic-vertex",
            provider: "anthropic-vertex",
            baseUrl: "https://aiplatform.googleapis.com",
            reasoning: true,
            input: ["text", "image"],
            cost: { input: 3, output: 15, cacheRead: 0.3, cacheWrite: 3.75 },
            contextWindow: 200000,
            maxTokens: 64000,
        },
        "claude-haiku-4-5": {
            id: "claude-haiku-4-5",
            name: "Claude Haiku 4.5 (Vertex)",
            api: "anthropic-vertex",
            provider: "anthropic-vertex",
            baseUrl: "https://aiplatform.googleapis.com",
            reasoning: true,
            input: ["text", "image"],
            cost: { input: 1, output: 5, cacheRead: 0.1, cacheWrite: 1.25 },
            contextWindow: 200000,
            maxTokens: 64000,
        },
    },
    "azure-openai-responses": {`,
    "models.generated: anthropic-vertex add Haiku 4.5",
    `"Claude Haiku 4.5 (Vertex)"`,
  );
}

// ── 5. provider-display-names.js ─────────────────────────────────────────
{
  const f = join(PI_PKG, "dist/core/provider-display-names.js");
  patch(
    f,
    `    anthropic: "Anthropic",
    "amazon-bedrock": "Amazon Bedrock",`,
    `    anthropic: "Anthropic",
    "anthropic-vertex": "Anthropic on Vertex AI",
    "amazon-bedrock": "Amazon Bedrock",`,
    "provider-display-names: anthropic-vertex",
  );
}

// ── 6. model-resolver.js: default model ──────────────────────────────────
{
  const f = join(PI_PKG, "dist/core/model-resolver.js");
  patch(
    f,
    `    "amazon-bedrock": "us.anthropic.claude-opus-4-6-v1",
    anthropic: "claude-opus-4-7",`,
    `    "amazon-bedrock": "us.anthropic.claude-opus-4-6-v1",
    anthropic: "claude-opus-4-7",
    "anthropic-vertex": "claude-opus-4-7",`,
    "model-resolver: defaultModelPerProvider",
  );
}

// ── 7. google-shared.js: trust thought_signature as opaque token ─────────
//
// Vertex docs describe `thought_signature` as an opaque string token —
// the encoding is NOT promised to be standard base64 (could be URL-safe,
// unpadded, etc.). The original strict regex silently dropped valid
// signatures from Google's own response, which on Gemini 3 surfaces as a
// 400 on the next function-calling turn (since signatures are mandatory).
// See https://docs.cloud.google.com/vertex-ai/generative-ai/docs/thought-signatures
{
  const f = join(PI_AI, "dist/providers/google-shared.js");
  patch(
    f,
    `// Thought signatures must be base64 for Google APIs (TYPE_BYTES).
const base64SignaturePattern = /^[A-Za-z0-9+/]+={0,2}$/;
function isValidThoughtSignature(signature) {
    if (!signature)
        return false;
    if (signature.length % 4 !== 0)
        return false;
    return base64SignaturePattern.test(signature);
}`,
    `// Patched (digi-setu/patches): thought_signature is an opaque string
// token per Vertex docs. Validating it as standard base64 silently drops
// signatures from Google's own response, breaking Gemini 3 function calling.
// Trust whatever the SDK returned.
function isValidThoughtSignature(signature) {
    return typeof signature === "string" && signature.length > 0;
}`,
    "google-shared: drop strict base64 validator",
    "thought_signature is an opaque string",
  );
}

// ── 8. google-shared.js: cross-model functionCall replay uses the
//      documented `skip_thought_signature_validator` escape hatch instead
//      of silently omitting the signature (which 400s on Gemini 3). ──────
{
  const f = join(PI_AI, "dist/providers/google-shared.js");
  patch(
    f,
    `                else if (block.type === "toolCall") {
                    const thoughtSignature = resolveThoughtSignature(isSameProviderAndModel, block.thoughtSignature);
                    const part = {
                        functionCall: {
                            name: block.name,
                            args: block.arguments ?? {},
                            ...(requiresToolCallId(model.id) ? { id: block.id } : {}),
                        },
                        ...(thoughtSignature && { thoughtSignature }),
                    };
                    parts.push(part);
                }`,
    `                else if (block.type === "toolCall") {
                    // Patched (digi-setu/patches): Gemini 3 returns 400 on a
                    // functionCall replay without thought_signature. Use the
                    // documented escape hatch for cross-model history; otherwise
                    // pass through the captured signature as-is.
                    const sameModelSig = resolveThoughtSignature(isSameProviderAndModel, block.thoughtSignature);
                    const thoughtSignature = sameModelSig ?? "skip_thought_signature_validator";
                    const part = {
                        functionCall: {
                            name: block.name,
                            args: block.arguments ?? {},
                            ...(requiresToolCallId(model.id) ? { id: block.id } : {}),
                        },
                        thoughtSignature,
                    };
                    parts.push(part);
                }`,
    "google-shared: skip_thought_signature_validator on cross-model toolCall",
    "skip_thought_signature_validator",
  );
}

// ── 9. transform-messages.js: same escape hatch on cross-model toolCall
//      replay (this gate runs before convertMessages, so we have to fix
//      both places). ────────────────────────────────────────────────────
{
  const f = join(PI_AI, "dist/providers/transform-messages.js");
  patch(
    f,
    `                if (block.type === "toolCall") {
                    const toolCall = block;
                    let normalizedToolCall = toolCall;
                    if (!isSameModel && toolCall.thoughtSignature) {
                        normalizedToolCall = { ...toolCall };
                        delete normalizedToolCall.thoughtSignature;
                    }`,
    `                if (block.type === "toolCall") {
                    const toolCall = block;
                    let normalizedToolCall = toolCall;
                    if (!isSameModel && toolCall.thoughtSignature) {
                        // Patched (digi-setu/patches): Gemini 3 rejects
                        // function-call replays without thought_signature. When
                        // transferring history from a different model, use the
                        // documented escape hatch instead of silently stripping.
                        normalizedToolCall = { ...toolCall, thoughtSignature: "skip_thought_signature_validator" };
                    }`,
    "transform-messages: skip_thought_signature_validator on cross-model toolCall",
    "skip_thought_signature_validator",
  );
}

// ── 11. google-vertex.js: honour GOOGLE_VERTEX_BASE_URL when set ────────
//
// The ``@google/genai`` SDK natively respects ``GOOGLE_VERTEX_BASE_URL``
// — but ONLY when ``httpOptions.baseUrl`` isn't supplied to the
// constructor. pi-ai's ``google-vertex.js`` wrapper passes a hardcoded
// ``model.baseUrl`` (e.g. ``"https://aiplatform.googleapis.com"``)
// from ``models.generated.js``, which silently overrides the env var.
//
// For the desktop "local pi via cloud relay" path
// (``services/relay_spawn.py``) we need to redirect pi's Vertex SDK at
// our localhost JWT-injecting proxy. Patching the wrapper to prefer
// the env var when set is the smallest possible change — model
// registry stays identical, and the env var is a no-op everywhere
// else (cloud build doesn't set it, BYOK doesn't set it).
//
// We also short-circuit GoogleAuth for the same flavour: when the
// base URL is localhost-relay we pass a fake ``apiKey`` so the SDK
// skips its ADC dance (line 19467 of @google/genai/dist/node/index.cjs
// constructs ``new GoogleAuth(...)`` ONLY when no apiKey is set —
// otherwise it sends ``Authorization: Bearer <apiKey>`` which our
// relay strips and replaces with the real ADC bearer upstream).
// Without this short-circuit, the SDK awaits ``getRequestHeaders()``
// which probes the GCE metadata server (169.254.169.254) on a laptop
// for ~15s × retries and the chat hangs forever on "streaming…".
{
  const f = join(PI_AI, "dist/providers/google-vertex.js");
  patch(
    f,
    `function buildHttpOptions(model, optionsHeaders) {
    const httpOptions = {};
    const baseUrl = resolveCustomBaseUrl(model.baseUrl);`,
    `function buildHttpOptions(model, optionsHeaders) {
    const httpOptions = {};
    // Patched (digi-setu/patches §11): GOOGLE_VERTEX_BASE_URL wins
    // over model.baseUrl. Used by the desktop local-pi-via-relay path
    // so the SDK posts to our localhost proxy instead of Vertex
    // directly. Without this patch the env var is silently shadowed.
    const envBaseUrl = (process.env.GOOGLE_VERTEX_BASE_URL || "").trim();
    const baseUrl = envBaseUrl || resolveCustomBaseUrl(model.baseUrl);`,
    "google-vertex: prefer GOOGLE_VERTEX_BASE_URL env over model.baseUrl",
    "GOOGLE_VERTEX_BASE_URL wins over model.baseUrl",
  );

  // Short-circuit GoogleAuth when targeting the localhost relay.
  // Replace `createClient` so it routes through createClientWithApiKey
  // with a placeholder API key, which sidesteps the ADC walk entirely.
  // The cloud relay rewrites the bearer regardless of what the SDK
  // ships — so the placeholder key is an inert token, not a credential.
  patch(
    f,
    `function createClient(model, project, location, optionsHeaders) {
    return new GoogleGenAI({
        vertexai: true,
        project,
        location,
        apiVersion: API_VERSION,
        httpOptions: buildHttpOptions(model, optionsHeaders),
    });
}`,
    `function createClient(model, project, location, optionsHeaders) {
    // Patched (digi-setu/patches §11b): when running through the
    // desktop's localhost relay proxy, swap the Vertex auth flow for
    // an apiKey-flavoured client. @google/genai constructs
    // GoogleAuth only when no apiKey is provided; with apiKey set
    // the SDK sends "Authorization: Bearer <apiKey>" and our local
    // proxy strips/replaces it before forwarding to the cloud relay.
    // Stops the chat from hanging forever on metadata-server probes
    // when the laptop has no ADC.
    const envBaseUrl = (process.env.GOOGLE_VERTEX_BASE_URL || "").trim();
    const isLocalRelay = /^https?:\\/\\/(127\\.0\\.0\\.1|localhost)\\b/i.test(envBaseUrl);
    if (isLocalRelay) {
        return new GoogleGenAI({
            vertexai: true,
            apiKey: "relay-managed",
            apiVersion: API_VERSION,
            httpOptions: buildHttpOptions(model, optionsHeaders),
        });
    }
    return new GoogleGenAI({
        vertexai: true,
        project,
        location,
        apiVersion: API_VERSION,
        httpOptions: buildHttpOptions(model, optionsHeaders),
    });
}`,
    "google-vertex: short-circuit GoogleAuth on localhost relay",
    "Patched (digi-setu/patches §11b)",
  );
}

// ── 10. google-shared.js: one-line debug log when a signature is dropped.
//       Quiet by default, gated on PI_VERTEX_GEMINI_DEBUG. ───────────────
{
  const f = join(PI_AI, "dist/providers/google-shared.js");
  patch(
    f,
    `/**
 * Only keep signatures from the same provider/model and with valid base64.
 */
function resolveThoughtSignature(isSameProviderAndModel, signature) {
    return isSameProviderAndModel && isValidThoughtSignature(signature) ? signature : undefined;
}`,
    `/**
 * Only keep signatures from the same provider/model.
 *
 * Patched (digi-setu/patches): emit a one-line trace so operators can
 * audit why a signature got dropped. Quiet by default; gate on
 * PI_VERTEX_GEMINI_DEBUG=1 to avoid spamming production logs.
 */
function resolveThoughtSignature(isSameProviderAndModel, signature) {
    const ok = isSameProviderAndModel && isValidThoughtSignature(signature);
    if (!ok && signature && process.env.PI_VERTEX_GEMINI_DEBUG) {
        console.error(\`[google-shared] thoughtSignature dropped (sameModel=\${isSameProviderAndModel}, len=\${signature.length})\`);
    }
    return ok ? signature : undefined;
}`,
    "google-shared: log dropped signatures under PI_VERTEX_GEMINI_DEBUG",
    "thoughtSignature dropped (sameModel=",
  );
}

console.log("\n── all edits applied ──");
