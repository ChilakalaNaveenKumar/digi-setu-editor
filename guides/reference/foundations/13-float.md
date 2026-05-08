# Foundations / 13 — `float`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/float/>
> **Audience:** an LLM agent. Original prose; technical facts about the `float` type. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/13-float/`).

---

## What it is

`float` is Typst's IEEE 754 64-bit (binary64 / "double") floating-point number. It is the default numeric type for fractional values, trigonometric calculations, and any non-exact numeric work. For exact base-10 arithmetic (currency, audited totals), see `decimal` instead.

---

## Literals

| Form | Meaning |
|---|---|
| `3.14` | Standard decimal literal. |
| `1e4` / `1.5e-3` | Exponential notation. |
| Anywhere a `float` is expected | An `int` is auto-promoted. |

`10 / 4` is `2.5` (the `/` operator on two integers returns `float` if not exact).

---

## Constructor

`float(value) -> float` accepts:

| Input type | Behavior |
|---|---|
| `bool` | `true → 1.0`, `false → 0.0`. |
| `int` | Exact for `|x| < 2^53`. Beyond that, nearest representable. |
| `float` | Identity. |
| `ratio` | Divides by `100%`. `float(40%) == 0.4`. |
| `str` | Parsed in base 10; supports exponential notation. |
| `decimal` | Casts to nearest representable float. |

- **Example:** [`01-literals-and-construction.typ`](./examples/13-float/01-literals-and-construction.typ)

---

## Special values & predicates

| Value / call | What it is |
|---|---|
| `float.nan` | NaN. **`x == float.nan` is ALWAYS false** — even if `x` is itself a NaN. Always use the predicate. |
| `float.inf` | Positive infinity. Use `-float.inf` for negative. |
| `float.is-nan(x)` | `bool` — true iff `x` is any NaN bit-pattern. |
| `float.is-infinite(x)` | `bool` — true iff `x` is `+inf` or `-inf`. |
| `x.signum()` | `1.0` for positive (incl. `+0.0`), `-1.0` for negative (incl. `-0.0`), `float.nan` for NaN. |

- **Example:** [`02-nan-inf-signum.typ`](./examples/13-float/02-nan-inf-signum.typ)

---

## IEEE 754 byte conversion

| Method | Notes |
|---|---|
| `x.to-bytes(endian: "little", size: 8) -> bytes` | `size` MUST be 4 (binary32) or 8 (binary64). Default 8. `endian` `"little"` (default) or `"big"`. |
| `float.from-bytes(b, endian: "little") -> float` | `b.len()` MUST be 4 or 8; format inferred from length. |

Use these for binary file I/O — e.g. reading a binary32 sensor reading from a buffer.

- **Example:** [`03-bytes-roundtrip.typ`](./examples/13-float/03-bytes-roundtrip.typ)

---

## Pitfalls (agent-targeted)

1. **`x == float.nan` is always false.** Use `float.is-nan(x)`. Comparison operators have IEEE NaN semantics — `nan < x`, `nan > x`, `nan == x` are all false.
2. **`+0.0 == -0.0` is true,** but `signum()` distinguishes them.
3. **Float arithmetic is not associative or distributive.** `(0.1 + 0.2) + 0.3` and `0.1 + (0.2 + 0.3)` may differ. Use `decimal` if exactness matters.
4. **`float(huge_string)` parses to `float.inf` if it overflows,** rather than erroring. Validate input ranges.
5. **`float(decimal(...))` is allowed and explicit;** the lossy direction is `decimal(float(...))`, which warns.
6. **Trig and log functions are float-only.** They do not accept `decimal`. Cast first if needed.

---

## Self-check

1. Are you using `float.is-nan(x)` for NaN tests, never `==`?
2. If you need exact base-10 arithmetic, are you using `decimal` instead of `float`?
3. For binary I/O, did you pass the right `size:` (4 vs 8) and `endian:`?
4. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
