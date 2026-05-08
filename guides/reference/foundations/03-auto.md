# Foundations / 03 — `auto`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/auto/>
> **Audience:** an LLM agent. Original prose; technical facts about the `auto` value. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/03-auto/`).

---

## What it is

`auto` is a **singleton value** of its own type (also called `auto`). It signals "let the function pick a smart, context-dependent default." It is **not** a synonym for `none`, `false`, zero, the empty string, or anything else — it has its own distinct identity.

Functions accept `auto` only on parameters that explicitly support contextual defaults. The reference page for each function indicates which parameters do.

- **Example (singleton properties):** [`01-auto-singleton.typ`](./examples/03-auto/01-auto-singleton.typ)
- **Example (using as a parameter value):** [`02-auto-as-param.typ`](./examples/03-auto/02-auto-as-param.typ)

---

## Mental model

| Sentinel | Meaning |
|---|---|
| `none` | "There is no value here." Function should treat the slot as absent or skip whatever it controls. |
| `auto` | "There IS a value here — but you, the function, figure out what it should be." |
| explicit value (e.g. `12pt`, `"de"`, `red`) | "Use exactly this; do not infer." |

`auto` is the middle option: the parameter is being *set* (the slot is non-empty), but the function decides the concrete value based on its surroundings.

---

## Common parameters that accept `auto`

These are the patterns the agent will run into most often:

| Function (param) | What `auto` means |
|---|---|
| `box(width: auto)`, `block(width: auto)` | Container is exactly as wide as its content. |
| `image(width: auto, height: auto)` | Use the image's intrinsic dimensions, scaled to fit. |
| `page(margin: auto)` | Use Typst's smart per-paper-size default margin. |
| `text(dir: auto)` | Derive direction (LTR/RTL) from the text language. |
| `text(top-edge: auto, bottom-edge: auto)` | Use font-metrics-driven defaults. |
| `grid(columns: auto)`, `table(columns: auto)` | Each column sized to its content. |

The pattern is: **layout-related sizing or direction parameters that have a "DWIM" default** typically take `auto`.

---

## Pitfalls

1. `auto == none` is `false`. They are different singletons of different types.
2. `if param == auto { ... }` works, but most checks should be: "is there a smart default to use, or did the caller give an explicit value?" — and most functions handle that internally so you usually don't compare.
3. `auto` cannot be used as a boolean. `if auto { ... }` is a type error.
4. Not every parameter accepts `auto`. Passing it where it isn't supported will be rejected with a type error citing the allowed types.

---

## Self-check

1. Are you reaching for `auto` (smart default) when you mean it, vs. `none` (absent), vs. an explicit value (forced)?
2. Did you confirm the parameter actually accepts `auto`? (Check the function's reference page.)
3. Are you treating `auto` and `none` as distinct in any conditional that handles both?
4. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
