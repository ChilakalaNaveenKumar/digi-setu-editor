#!/usr/bin/env node
// Direct AnthropicVertex call against the codly corpus — no pi in the loop.
// Times the full request and prints token + cache stats so we can tell whether
// the slowness lives in pi or in the API call itself.

import { AnthropicVertex } from "@anthropic-ai/vertex-sdk";
import { promises as fs } from "node:fs";
import path from "node:path";

const project = process.env.GOOGLE_CLOUD_PROJECT;
const region = process.env.PI_VERTEX_ANTHROPIC_LOCATION ?? "global";
const model = process.env.PI_TYPST_ROUTER_MODEL ?? "claude-haiku-4-5";
if (!project) throw new Error("GOOGLE_CLOUD_PROJECT not set");

const guidesRoot = path.join(process.cwd(), "guides");

async function walk(dir) {
  const out = [];
  for (const e of await fs.readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...(await walk(full)));
    else if (e.isFile() && (e.name.endsWith(".md") || e.name.endsWith(".typ"))) out.push(full);
  }
  return out;
}

console.log(`── load codly corpus ──`);
const t0 = Date.now();
const all = await walk(guidesRoot);
const codly = all.filter((p) => p.includes("/guides/codly/"));
let corpus = "";
for (const f of codly) {
  const rel = `guides/${path.relative(guidesRoot, f)}`;
  const body = await fs.readFile(f, "utf8");
  corpus += `---\n# FILE: ${rel}\n---\n${body}\n\n`;
}
console.log(`  loaded ${codly.length} files, ${corpus.length} bytes (~${Math.round(corpus.length / 4)} tokens) in ${Date.now() - t0}ms`);

const query =
  "How do I reduce vertical spacing between lines in a codly code block? `set par(leading: ...)` inside `#show raw: it => {...}` does nothing. What actually works?";

const ant = new AnthropicVertex({ projectId: project, region });

console.log(`\n── call ${model} (region=${region}) — first call, no cache yet ──`);
const t1 = Date.now();
let res;
try {
  res = await ant.messages.create({
    model,
    max_tokens: 2048,
    temperature: 0.2,
    system:
      "You're a senior engineer who knows the Codly Typst package cold. Codly: code-block styling — `codly()`, `codly-init`, line numbers, language pills, highlights.",
    messages: [
      {
        role: "user",
        content: [
          {
            type: "text",
            text: `The full codly corpus follows. Read what you need; ignore the rest.\n\n${corpus}`,
            cache_control: { type: "ephemeral" },
          },
          {
            type: "text",
            text: `Be dense and concrete. Show the exact import lines and 5-30 line copy-paste examples. Cite the doc paths you pulled from at the bottom under "Sources:".\n\nThe user's brief:\n${query}`,
          },
        ],
      },
    ],
  });
} catch (err) {
  console.error(`  FAILED after ${Date.now() - t1}ms:`, err.message);
  if (err.status) console.error(`  HTTP ${err.status}`);
  if (err.error) console.error(`  body:`, JSON.stringify(err.error).slice(0, 400));
  process.exit(1);
}
const elapsed = Date.now() - t1;
console.log(`  responded in ${elapsed}ms`);
console.log(`  usage:`, JSON.stringify(res.usage));
console.log(`\n── answer (first 60 lines) ──`);
const text = res.content.filter((b) => b.type === "text").map((b) => b.text).join("\n");
console.log(text.split("\n").slice(0, 60).join("\n"));

console.log(`\n── 2nd call — same corpus, different question, cache should hit ──`);
const t2 = Date.now();
const res2 = await ant.messages.create({
  model,
  max_tokens: 800,
  temperature: 0.2,
  system:
    "You're a senior engineer who knows the Codly Typst package cold. Codly: code-block styling — `codly()`, `codly-init`, line numbers, language pills, highlights.",
  messages: [
    {
      role: "user",
      content: [
        {
          type: "text",
          text: `The full codly corpus follows. Read what you need; ignore the rest.\n\n${corpus}`,
          cache_control: { type: "ephemeral" },
        },
        {
          type: "text",
          text: `What's the import line for codly 1.3.0?`,
        },
      ],
    },
  ],
});
console.log(`  responded in ${Date.now() - t2}ms`);
console.log(`  usage:`, JSON.stringify(res2.usage));
