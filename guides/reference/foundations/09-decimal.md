# Foundations / 09 — `decimal`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/decimal/>
> **Audience:** an LLM agent. Original prose; technical facts about the `decimal` type. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/09-decimal/`).

---

## What it is

`decimal` is a **fixed-point base-10 numeric type**. Use it whenever you need exact fractional arithmetic — currency totals, audited invoice math, exact percentages, anything where `0.1 + 0.2 != 0.3` would be a bug.

It is the trade-off type: more memory and slower than `float`, but **exact** for the operations it supports.

---

## Construction (THE most important section)

| Form | OK? | Notes |
|---|---|---|
| `decimal("3.14")` | YES — recommended | String literal preserves every digit you wrote. |
| `decimal(59)` | YES — exact | Integer cast is lossless. |
| `decimal(true)` / `decimal(false)` | YES | Casts to `1` / `0`. Mostly a curiosity. |
| `decimal(other_decimal)` | YES | Identity. |
| `decimal(3.14)` | DISCOURAGED — emits a compiler **warning** | Float→decimal is inherently imprecise. The bits of `3.14` aren't really `3.14`. |

**Rule of thumb for the agent:** when you write a numeric literal that you want stored as `decimal`, type it as a quoted string. `decimal("0.1")`, never `decimal(0.1)`.

- **Example:** [`01-precision-and-string-ctor.typ`](./examples/09-decimal/01-precision-and-string-ctor.typ)

---

## Precision & limits

- **Significant digits:** ~28–29 base-10 digits total (sum of integer and fractional parts).
- **Maximum magnitude:** ±79,228,162,514,264,337,593,543,950,335 (i.e. `(2^96 - 1)`).
- **No infinity, no NaN.** Operations that would over/underflow raise an error.
- Addition, subtraction, multiplication, and `pow(d, int_exponent)` are **exact** as long as the result fits in the digit budget. Multiplication and division can push fractional digits past the limit, in which case the trailing digits round.

---

## Arithmetic — what is and isn't allowed

| Operation | Behavior |
|---|---|
| `decimal +-*/` `decimal` | Exact within precision limits. |
| `decimal +-*/` `int` | Allowed; `int` is promoted to decimal. Exact. |
| `decimal +-*/` `float` | **ERROR.** Intentional — would silently destroy precision. |

To opt into mixed-precision arithmetic explicitly, cast: `float(my_decimal) * 0.1`.

- **Example:** [`02-arithmetic-and-int-mixing.typ`](./examples/09-decimal/02-arithmetic-and-int-mixing.typ)

---

## `decimal` and `calc`

| Function category | Decimal support |
|---|---|
| `abs`, `min`, `max`, `clamp` | YES — return `decimal`. |
| `floor`, `ceil`, `trunc` | YES — but return `int`. Errors if magnitude exceeds int64 range. |
| `round(value, digits: n)`, `fract(value)` | YES — return `decimal` (same type as input). |
| `pow(decimal_base, int_exponent)` | YES — returns `decimal`. |
| `pow(decimal_base, float_exponent)` | NO. |
| `sqrt`, `root`, `exp`, `log`, `ln`, `sin`, `cos`, `tan`, `atan2`, hyperbolics | NO — `float`-only. Cast with `float(...)` if needed. |

- **Example:** [`03-decimal-with-calc.typ`](./examples/09-decimal/03-decimal-with-calc.typ)

---

## Display & string conversion

| Goal | Use |
|---|---|
| Insert a decimal into the document | Just `#my_decimal` (markup interpolation). |
| Limit displayed digits | Pre-round: `#calc.round(my_decimal, digits: 2)`. |
| Get a string for post-processing (e.g. `.` → `,` for European format) | `str(my_decimal)`, then string methods. |

There is **no built-in localization yet** (no thousands separator, no comma decimal). Implement that yourself via `str()` + `replace`.

---

## Pitfalls (agent-targeted)

1. **`decimal(3.14)` is a smell.** It compiles with a warning but is wrong-by-design. Always reach for `decimal("3.14")`.
2. **Don't mix `decimal` and `float` in arithmetic.** Even multiplying by `1.0` will refuse. Cast explicitly with `float(d)` if that's what you meant.
3. **`floor`/`ceil`/`trunc` on a decimal return `int`,** not `decimal`. Use `round(d, digits: 0)` if you want to stay in decimal-land.
4. **No infinity / NaN.** Defensive code that tests for `float.inf` won't apply; over/underflow is a hard error you must avoid via `clamp` or branching.
5. **String comparison after `str(d)` may not be what you expect** — leading zeros, trailing zeros, sign handling. Compare values as `decimal`, format only at the very end.

---

## When NOT to use `decimal`

- When you only need approximate values (rendering math previews, scientific calculations).
- When you need transcendental functions (sin/cos/log/sqrt/etc.) on the value.
- When the data is already a measured float and adding `decimal` precision is a lie.

For these, stay with `float`.

---

## Self-check

1. For every fractional literal that needs to be exact, did you type `decimal("...")` (quoted)?
2. Did you keep the entire computation inside `decimal` (or `decimal` mixed with `int`), without crossing into `float`?
3. If you needed a transcendental function, did you cast explicitly with `float(d)` and accept the precision loss?
4. Does the result fit in 28–29 digits across the entire computation?
5. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
