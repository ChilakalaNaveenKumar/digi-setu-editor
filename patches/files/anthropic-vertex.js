// anthropic-vertex.js — Vertex-flavoured Anthropic provider.
//
// Pattern: mirror google-vertex.js (resolve project+location from env, use
// Application Default Credentials), but reuse the Anthropic Messages stream
// machinery from anthropic.js by injecting a pre-built AnthropicVertex client
// through `options.client` (already supported on line ~299 of anthropic.js).
//
// Why we don't just call streamSimpleAnthropic with options.client:
//   streamSimpleAnthropic strips options through buildBaseOptions() (which
//   does NOT carry `client`), and it requires an apiKey to even start. So we
//   replicate its tiny adaptive-thinking dispatch here, then call
//   streamAnthropic directly with `client` preserved.
//
// Auth precedence (matches google-vertex.js conventions):
//   project  : options.project  || PI_VERTEX_ANTHROPIC_PROJECT  || GOOGLE_CLOUD_PROJECT  || GCLOUD_PROJECT
//   location : options.location || PI_VERTEX_ANTHROPIC_LOCATION || GOOGLE_CLOUD_LOCATION || "global"
//
// Patched in by /Users/chilakalanaveenkumar/workarea/PR reviews/pi-typst-test/patches/
// Reapply via `bash patches/apply.sh` after `pi update`.
import { AnthropicVertex } from "@anthropic-ai/vertex-sdk";
import { mapThinkingLevelToEffort, streamAnthropic, supportsAdaptiveThinking, } from "./anthropic.js";
import { adjustMaxTokensForThinking, buildBaseOptions, } from "./simple-options.js";

function resolveProject(options) {
    const project = options?.project
        || process.env.PI_VERTEX_ANTHROPIC_PROJECT
        || process.env.GOOGLE_CLOUD_PROJECT
        || process.env.GCLOUD_PROJECT;
    if (!project) {
        throw new Error("anthropic-vertex requires a project ID. Set GOOGLE_CLOUD_PROJECT (or PI_VERTEX_ANTHROPIC_PROJECT) or pass project in options.");
    }
    return project;
}

function resolveLocation(options) {
    return options?.location
        || process.env.PI_VERTEX_ANTHROPIC_LOCATION
        || process.env.GOOGLE_CLOUD_LOCATION
        || "global";
}

function buildClient(options) {
    return new AnthropicVertex({
        region: resolveLocation(options),
        projectId: resolveProject(options),
    });
}

export const streamAnthropicVertex = (model, context, options) => {
    const client = options?.client ?? buildClient(options);
    if (process.env.PI_VERTEX_ANTHROPIC_DEBUG) {
        console.error(`[anthropic-vertex] stream client=${client?.constructor?.name} region=${client?.region} project=${client?.projectId}`);
    }
    return streamAnthropic(model, context, { ...options, client });
};

export const streamSimpleAnthropicVertex = (model, context, options) => {
    const client = options?.client ?? buildClient(options);
    if (process.env.PI_VERTEX_ANTHROPIC_DEBUG) {
        console.error(`[anthropic-vertex] streamSimple client=${client?.constructor?.name} region=${client?.region} project=${client?.projectId}`);
    }
    // buildBaseOptions strips `client` and requires an apiKey for its second arg
    // shape — feed a placeholder, then re-inject the real client.
    const base = buildBaseOptions(model, options, "<vertex-adc>");
    const withClient = { ...base, client };
    if (!options?.reasoning) {
        return streamAnthropic(model, context, { ...withClient, thinkingEnabled: false });
    }
    if (supportsAdaptiveThinking(model.id)) {
        const effort = mapThinkingLevelToEffort(model, options.reasoning);
        return streamAnthropic(model, context, {
            ...withClient,
            thinkingEnabled: true,
            effort,
        });
    }
    const adjusted = adjustMaxTokensForThinking(base.maxTokens || 0, model.maxTokens, options.reasoning, options.thinkingBudgets);
    return streamAnthropic(model, context, {
        ...withClient,
        maxTokens: adjusted.maxTokens,
        thinkingEnabled: true,
        thinkingBudgetTokens: adjusted.thinkingBudget,
    });
};
//# sourceMappingURL=anthropic-vertex.js.map
