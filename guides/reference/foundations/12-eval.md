# Foundations / 12 — `eval`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/eval/>
> **Audience:** an LLM agent. Original prose; technical facts about the `eval` function. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/12-eval/`).

---

## What it is

`eval(source, mode: "code", scope: (:))` parses a `str` of Typst source at compile time and returns whatever value that source produces. **It is the documented "last resort" tool** — the official docs explicitly say "should only be used as a last resort." For an agent, the rule of thumb is: if there's a way to do this with a normal `let` binding or a closure, use that instead.

---

## Signature

```
eval(
  source: str,
  mode:   str = "code",       // "code" | "markup" | "math"
  scope:  dictionary = (:),
) -> any
```

---

## Modes

| `mode` | Source is parsed as if… | Typical return type |
|---|---|---|
| `"code"` (default) | …it followed a `#` in code mode | any (the expression's value) |
| `"markup"` | …it were the body of a Typst file | `content` |
| `"math"` | …it were the body of an `$ ... $` math block | `content` |

- **Example:** [`01-modes-and-defaults.typ`](./examples/12-eval/01-modes-and-defaults.typ)

---

## `scope:` — passing values in

The `scope` dictionary is the ONLY way to expose caller-side values to the evaluated source. Without it, the source has access to **globals only** — local `let` bindings from the surrounding scope do NOT leak in.

```
#let x = 10
#eval("x + 1")              // ERROR: x is not defined inside the eval scope
#eval("x + 1", scope: (x: 10))   // 11
```

Scope values can be any type, including `content`, functions, etc.

- **Example:** [`02-scope.typ`](./examples/12-eval/02-scope.typ)

---

## Why this is a "last resort"

| Concern | Reason |
|---|---|
| **Editor / IDE doesn't see the source** | No completion, no go-to-definition, no rename. |
| **Errors point inside the string** | Stack traces and error spans are awkward. |
| **No protection against typos** | `eval("primt(x)")` will fail at runtime, not parse time. |
| **Performance** | Each `eval` call re-parses. |
| **Static analysis is impossible** | Tools can't infer what the result will be. |

If you find yourself calling `eval`, ask: can a `let` binding or closure replace it? Can a dictionary lookup replace it? Almost always, yes.

---

## Legitimate use cases (rare)

1. **User-supplied source code** that genuinely must be parsed at compile time (e.g. a user-controlled expression in a config file you `read(...)`).
2. **Bridging across `eval`-mode boundaries** (e.g. parsing a math source string into rendered math content).
3. **Driving a small DSL** where you genuinely have strings of Typst source as data.

If your reason isn't on this list, you don't need `eval`.

---

## Pitfalls (agent-targeted)

1. **No surrounding scope.** Pass everything you need via `scope:`.
2. **Mode default is `"code"`.** If you want markup or math, you MUST pass `mode:`.
3. **Errors inside the source surface at the `eval` call site,** not "in the string at column N" — debugging is harder than for normal code.
4. **`eval` runs at compile time,** so the source string must be a literal or a value computable at compile time. Reading from runtime data is not a thing here — Typst has no runtime in that sense.
5. **The result type is `any`.** Check / cast as needed.

---

## Self-check

1. Have you ruled out a normal `let` binding, closure, or dictionary lookup as an alternative?
2. Did you pass every variable you need into `scope:` ?
3. Did you set `mode:` if it's anything other than `"code"`?
4. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
