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

// When ANTHROPIC_VERTEX_BASE_URL points at a relay-style proxy
// (typically the desktop's localhost JWT-injecting proxy that forwards
// to our cloud Vertex passthrough), the proxy supplies its OWN bearer
// — we MUST NOT let the SDK try to resolve real ADC, because:
//   * On a user's laptop there is no ADC chain. The default GoogleAuth
//     code path eventually probes the GCE metadata server
//     (169.254.169.254) which on a Mac/Windows box hangs for the full
//     timeout (15+ s × retries) and the chat appears to "stream
//     forever". Setting the base URL alone is not enough — auth
//     happens BEFORE the first HTTP request, in `prepareOptions`.
//   * Even when ADC is present (operator dev box) we don't want it on
//     this code path because the cloud relay rewrites the project id
//     anyway, so the laptop-side bearer is throwaway. Burning cycles
//     on `getClient()` just to throw the bearer away is wasteful.
//
// We detect the relay flavour via a localhost base URL prefix. The
// stub auth client returns empty headers (the proxy replaces them
// with a fresh Clerk JWT) and exposes the resolved projectId so the
// SDK's `prepareOptions` skips its `getClient()` await entirely.
function _isLocalRelayBaseUrl(url) {
    if (!url || typeof url !== "string") return false;
    return /^https?:\/\/(127\.0\.0\.1|localhost)\b/i.test(url);
}

function resolveProject(options) {
    const project = options?.project
        || process.env.PI_VERTEX_ANTHROPIC_PROJECT
        || process.env.GOOGLE_CLOUD_PROJECT
        || process.env.GCLOUD_PROJECT;
    if (project) return project;
    // Relay short-circuit: when we're routing through the localhost
    // relay proxy the cloud side rewrites the project id, so the
    // value the SDK encodes in the URL path is cosmetic. Return a
    // placeholder so `new AnthropicVertex()` doesn't throw early.
    if (_isLocalRelayBaseUrl(process.env.ANTHROPIC_VERTEX_BASE_URL)) {
        return "relay-managed";
    }
    throw new Error("anthropic-vertex requires a project ID. Set GOOGLE_CLOUD_PROJECT (or PI_VERTEX_ANTHROPIC_PROJECT) or pass project in options.");
}

function resolveLocation(options) {
    return options?.location
        || process.env.PI_VERTEX_ANTHROPIC_LOCATION
        || process.env.GOOGLE_CLOUD_LOCATION
        || "global";
}

function buildClient(options) {
    const projectId = resolveProject(options);
    const region = resolveLocation(options);
    const baseUrl = process.env.ANTHROPIC_VERTEX_BASE_URL;
    const args = { region, projectId };
    if (_isLocalRelayBaseUrl(baseUrl)) {
        // Stub auth client — the SDK awaits authClient.getRequestHeaders()
        // and reads authClient.projectId in prepareOptions. By feeding
        // a synchronous shim we sidestep the GoogleAuth dance. The
        // empty header object is harmless: the localhost proxy
        // overwrites Authorization with the cached Clerk JWT before
        // forwarding upstream.
        args.authClient = {
            projectId,
            getRequestHeaders: async () => ({}),
        };
    }
    return new AnthropicVertex(args);
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
