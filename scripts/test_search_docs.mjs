#!/usr/bin/env node
// Direct test of the search_docs tool (the one in extensions/typst-tools.ts).
// We mock the pi ExtensionAPI, capture registered tools, then call .execute()
// straight on search_docs. No pi, no agent, no streaming — just the tool.
//
// Usage:
//   node --import tsx scripts/test_search_docs.mjs codly "your question here"
//   node --import tsx scripts/test_search_docs.mjs touying "how do themes work"
//
// Make sure scripts/env.sh has been sourced (or set GOOGLE_CLOUD_PROJECT,
// PI_TYPST_ROUTER_MODEL, PI_VERTEX_ANTHROPIC_LOCATION yourself).

const pkg = process.argv[2] ?? "codly";
const query =
  process.argv[3] ??
  "How do I reduce vertical line spacing inside a code block? `set par(leading: 0em)` inside `#show raw: it => {...}` does nothing.";

console.log("════════════════════════════════════════════════════════════════════");
console.log(`  search_docs direct test`);
console.log("════════════════════════════════════════════════════════════════════");
console.log(`  router model : ${process.env.PI_TYPST_ROUTER_MODEL ?? "(default)"}`);
console.log(`  region       : ${process.env.PI_VERTEX_ANTHROPIC_LOCATION ?? "(default)"}`);
console.log(`  package      : ${pkg}`);
console.log(`  query        : ${query.slice(0, 80)}${query.length > 80 ? "…" : ""}`);
console.log();

// ── mock the pi ExtensionAPI ──
const tools = new Map();
const mockPi = {
  registerTool: (cfg) => {
    tools.set(cfg.name, cfg);
  },
};

console.log("── loading extensions/typst-tools.ts ──");
const t0 = Date.now();
const mod = await import("../extensions/typst-tools.ts");
mod.default(mockPi);
console.log(`  registered ${tools.size} tools in ${Date.now() - t0}ms: ${[...tools.keys()].join(", ")}`);

const sd = tools.get("search_docs");
if (!sd) {
  console.error("ERROR: search_docs tool was not registered");
  process.exit(1);
}

console.log("\n── CALL #1 (cold cache) ──");
const t1 = Date.now();
const r1 = await sd.execute("test-1", { query, package: pkg });
console.log(`  elapsed: ${Date.now() - t1}ms`);
console.log(`  isError: ${r1.isError ?? false}`);
console.log(`  details: ${JSON.stringify(r1.details)}`);
console.log("\n  ── answer (first 50 lines) ──");
const text1 = r1.content.map((c) => c.text).join("\n");
console.log(text1.split("\n").slice(0, 50).join("\n"));

console.log("\n── CALL #2 (same package, warm cache, different query) ──");
const t2 = Date.now();
const r2 = await sd.execute("test-2", {
  query: "What's the import line for codly 1.3.0 and what's the codly-init show rule?",
  package: pkg,
});
console.log(`  elapsed: ${Date.now() - t2}ms`);
console.log(`  details: ${JSON.stringify(r2.details)}`);
const text2 = r2.content.map((c) => c.text).join("\n");
console.log("\n  ── answer (first 20 lines) ──");
console.log(text2.split("\n").slice(0, 20).join("\n"));

console.log("\n── summary ──");
console.log(`  cold call : ${Date.now() - t1 - (Date.now() - t2)}ms (corpus cache miss)`);
console.log(`  warm call : ${Date.now() - t2}ms (corpus cache hit)`);
