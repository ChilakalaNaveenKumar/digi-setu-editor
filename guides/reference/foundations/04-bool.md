# Foundations / 04 — `bool`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/bool/>
> **Audience:** an LLM agent. Original prose; technical facts about the `bool` type. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/04-bool/`).

---

## What it is

The `bool` type has exactly two values: `true` and `false`. It signals "active vs. inactive" and is the type produced by every comparison and logical operator. It is also what `if` and `while` consume as a condition, and what `assert(...)` requires for its first argument.

- **Example:** [`01-bool-values-and-ops.typ`](./examples/04-bool/01-bool-values-and-ops.typ)

---

## How `bool` values are produced

| Source | Examples |
|---|---|
| Literals | `true`, `false` |
| Comparison | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| Membership | `x in collection`, `x not in collection` |
| Logical | `not x`, `x and y`, `x or y` |

`==` and `!=` are value-based: arrays/dictionaries compare element-wise; `none == none` is `true`; `auto == auto` is `true`.

---

## Where `bool` is consumed

| Site | Notes |
|---|---|
| `if cond { … } else { … }` | `cond` must be `bool`. There is no truthiness coercion. `if 0 { … }` is a type error. |
| `while cond { … }` | Same. |
| `assert(cond, message: …)` | First arg must be `bool`. Same rule. |
| `bool` parameter slots on functions | Same. |

---

## Pitfalls

1. **No truthiness.** Empty strings, zero, `none`, `auto`, etc. are NOT coerced to `bool`. Always compare explicitly: `if name != "" { … }`, not `if name { … }`.
2. **Operator precedence:** `not` binds tighter than `and` / `or`. `not a and b` means `(not a) and b`. Use parentheses if you want `not (a and b)`.
3. **`and` / `or` short-circuit.** Right operand is not evaluated if the result is already determined.
4. `==` between values of different types is generally `false` rather than an error (e.g. `1 == "1"` is `false`). Be careful with int-vs-string comparisons in user data.

---

## Self-check

1. Are you passing a real bool to `if` / `while` / `assert`?
2. Did you remember `not / and / or` (the keywords) instead of `! / && / ||` (which are NOT Typst syntax)?
3. Are you relying on truthiness anywhere? (Don't.)
4. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
