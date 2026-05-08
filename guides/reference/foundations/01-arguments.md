# Foundations / 01 — `arguments`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/arguments/>
> **Audience:** an LLM agent. Original prose; technical facts about the `arguments` type. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/01-arguments/`).

---

## What it is

A value of type `arguments` represents **a captured set of function call arguments** — both positional and named — held as a single value that can be inspected and later forwarded.

You meet `arguments` in three places:
1. As the value bound by an **argument sink** parameter (`..name`).
2. As the result of the **`arguments(...)` constructor**.
3. As the operand of the **spread operator** `..value` at a call site.

---

## 1. Argument sink — capture varargs

- **Syntax:** put `..name` in a function's parameter list. It must come **last** in the parameter list. The parameter binds to an `arguments` value containing every excess positional and named argument the caller supplied.
- **Example:** [`01-argument-sink.typ`](./examples/01-arguments/01-argument-sink.typ)
- **Pitfalls:**
  - Only one sink per parameter list.
  - The sink captures both positional AND named arguments. Use `.pos()` and `.named()` to separate them.
  - Without a sink, extra arguments are a compile error.

## 2. Spread operator at a call site

- **Syntax:** `..value` inside an argument list, where `value` is one of:
  - an `arguments` value — both positional and named are forwarded
  - an `array` — items become positional arguments
  - a `dictionary` — entries become named arguments
- **Example:** [`02-spread-array-and-dict.typ`](./examples/01-arguments/02-spread-array-and-dict.typ)
- **Pitfalls:**
  - The spread operator and the sink syntax look identical (`..x`). Position determines meaning: in a parameter list it is a sink (collects); in an argument list it is a spread (expands).
  - Spreading a non-array/non-dict/non-arguments value is an error.
  - Order of arguments still matters after spreading. Positional spreads contribute in the order they appear at the call site.

## 3. The `arguments(...)` constructor

- **Syntax:** `arguments(positional1, positional2, ..., named1: v1, named2: v2)` — captures whatever you pass exactly as if it were a function's incoming arguments. Equivalent to `let make(..sink) = sink`.
- **Example:** [`03-arguments-constructor-and-methods.typ`](./examples/01-arguments/03-arguments-constructor-and-methods.typ)
- **Use case:** preconfigure a bundle of styling once, then spread it into multiple call sites for consistency:
  ```
  #let card-style = arguments(stroke: 0.5pt, inset: 8pt, radius: 4pt)
  #box(..card-style)[First card]
  #box(..card-style)[Second card]
  ```

---

## Methods

| Method | Returns | Notes |
|---|---|---|
| `args.pos()` | `array` | All captured positional arguments, in order. |
| `args.named()` | `dictionary` | All captured named arguments. |
| `args.at(index)` | any | Positional arg at integer index — same as `args.pos().at(index)`. |
| `args.at(name)` | any | Named arg by string name — same as `args.named().at(name)`. |
| `args.at(key, default: x)` | any | As above, but returns `x` when the key is missing instead of erroring. |

---

## Pitfalls (recap, agent-targeted)

1. `..` is **sink** in a parameter list, **spread** in an argument list. Same characters, opposite directions.
2. The sink parameter must be **last** in the parameter list.
3. `args.pos()` and `args.named()` are **separate collections** — neither contains the other.
4. To pass an arguments bundle on, spread it (`..bundle`); do not try to pass it as a single positional value.

---

## Self-check

1. Did you put `..sink` last in the parameter list?
2. When forwarding, are you using `..bundle` (spread) and not `bundle` (single value)?
3. Did you account for both positional and named when consuming the sink?
4. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
