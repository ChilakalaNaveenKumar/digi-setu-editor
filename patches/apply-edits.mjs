#!/usr/bin/env node
// patches/apply-edits.mjs — idempotent in-place patches for pi-coding-agent
// + pi-ai. Called by apply.sh.
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const PI_PKG = process.argv[2];
if (!PI_PKG) {
  console.error("usage: node apply-edits.mjs <pi-coding-agent-dir>");
  process.exit(1);
}
const PI_AI = join(PI_PKG, "node_modules", "@mariozechner", "pi-ai");

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

console.log("\n── all edits applied ──");
