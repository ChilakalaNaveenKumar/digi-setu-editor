# Foundations / 02 — `assert`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/assert/>
> **Audience:** an LLM agent. Original prose; technical facts about the `assert` family. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/02-assert/`).

---

## What it is

`assert` is a compile-time guard. When the asserted condition is true, it produces nothing. When false, it **fails the entire compile** with the supplied (or default) message — there is no "soft" assertion.

Use it as a contract check at the top of helper functions and templates: pre-validate inputs so an obvious error explains itself instead of cascading into a confusing layout failure later.

---

## 1. `assert(condition, message: "...")`

- **Signature:** `assert(condition: bool, message: str = none) -> none`
- **Behavior:** If `condition` is `true`, no output. If `false`, abort compile with `message` (or a default).
- **Example:** [`01-assert-basic.typ`](./examples/02-assert/01-assert-basic.typ)
- **Pitfalls:**
  - The condition must evaluate to `bool`. `assert(some-value)` (without a comparison) errors if `some-value` isn't already a boolean. Use `assert(some-value != none)` etc.
  - `message:` is a named argument. Don't pass it as a positional second arg.

## 2. `assert.eq(left, right, message: "...")`

- **Signature:** `assert.eq(left: any, right: any, message: str = none) -> none`
- **Behavior:** Fails if `left != right`. Default error message includes both values' representations — usually more useful than a hand-rolled string, so omit `message:` unless the values alone won't explain the failure.
- **Example:** [`02-assert-eq-ne.typ`](./examples/02-assert/02-assert-eq-ne.typ)

## 3. `assert.ne(left, right, message: "...")`

- **Signature:** `assert.ne(left: any, right: any, message: str = none) -> none`
- **Behavior:** Fails if `left == right`. Symmetric to `assert.eq`.

---

## When to use which

| Goal | Use |
|---|---|
| Predicate of any kind (`x > 0`, `arr.len() > 0`, `name in dict`, …) | `assert(...)` |
| "These two values must match" | `assert.eq(...)` (gets free actual-vs-expected message) |
| "These two values must differ" | `assert.ne(...)` |

---

## Pitfalls

1. Asserts run at **compile time**, not at "runtime in the document" — if the condition depends on user content, you can still get unexpected failures.
2. A failing `assert` halts the **whole compile**. Don't put speculative asserts in production templates without thinking about which inputs will trip them.
3. Equality is value-based, not reference-based. `assert.eq((1,2), (1,2))` passes.
4. `none == none` is `true`; `auto == auto` is `true`; but `none != auto` is `true` (they are different singletons).

---

## Self-check

1. Is the first arg to `assert(...)` a bool expression?
2. Is `message:` passed as a named argument (not positional)?
3. For equality checks, did you reach for `assert.eq` (better default message) over `assert(a == b)`?
4. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
