# Foundations / 06 — `calc` module

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/calc/>
> **Audience:** an LLM agent. Original prose; technical facts about the `calc` module. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/06-calc/`).

---

## What it is

`calc` is a built-in module of numerical functions and constants. It is **not auto-imported** — every usage is `calc.something(...)`. It is the standard place to find:

- Sign / extrema / clamping (`abs`, `min`, `max`, `clamp`)
- Rounding & integer parts (`floor`, `ceil`, `round`, `trunc`, `fract`)
- Powers, roots, exponentials, logarithms (`pow`, `sqrt`, `root`, `exp`, `log`, `ln`)
- Trigonometry (`sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`)
- Hyperbolic functions (`sinh`, `cosh`, `tanh`)
- Combinatorics & number theory (`fact`, `perm`, `binom`, `gcd`, `lcm`, `even`, `odd`)
- Division-family with sign control (`rem`, `rem-euclid`, `div-euclid`, `quo`)
- Vector norms (`norm`)
- Constants: `calc.pi`, `calc.tau`, `calc.e`, `calc.inf`

---

## Function reference (all in `calc.*`)

| Function | Signature | One-line summary |
|---|---|---|
| `abs` | `abs(x) -> any` | Absolute value. Accepts int/float/length/angle/ratio/fraction/decimal. |
| `min` | `min(..vs) -> any` | Minimum of args (≥ 1). Variadic. Works on any orderable type, including strings. |
| `max` | `max(..vs) -> any` | Maximum of args (≥ 1). Variadic. |
| `clamp` | `clamp(x, lo, hi) -> any` | Clamp `x` to inclusive `[lo, hi]`. |
| `floor` | `floor(x) -> int` | Round down to int. |
| `ceil` | `ceil(x) -> int` | Round up to int. |
| `trunc` | `trunc(x) -> int` | Drop fractional part toward zero. |
| `fract` | `fract(x) -> same` | Fractional part; sign matches input. |
| `round` | `round(x, digits: 0) -> same` | Round to N decimal places (or N integer significant digits if N < 0). Half away-from-zero. |
| `pow` | `pow(base, exp) -> num` | Base^exp. If base is decimal, exp must be int. |
| `sqrt` | `sqrt(x) -> float` | Square root. `x` must be ≥ 0. |
| `root` | `root(x, n) -> float` | Real n-th root. If `x < 0`, `n` must be odd. |
| `exp` | `exp(x) -> float` | e^x. |
| `log` | `log(x, base: 10.0) -> float` | Logarithm; default base 10. |
| `ln` | `ln(x) -> float` | Natural log (base e). |
| `sin` | `sin(angle) -> float` | Sine. Accepts `angle` (e.g. `90deg`) or plain number (interpreted as **radians**). |
| `cos` | `cos(angle) -> float` | Cosine. Same input rule as `sin`. |
| `tan` | `tan(angle) -> float` | Tangent. Same input rule. |
| `asin` | `asin(x) -> angle` | Arcsine. `x` in `[-1, 1]`. **Returns angle.** |
| `acos` | `acos(x) -> angle` | Arccosine. `x` in `[-1, 1]`. **Returns angle.** |
| `atan` | `atan(x) -> angle` | Arctangent. **Returns angle.** |
| `atan2` | `atan2(x, y) -> angle` | Four-quadrant arctangent. **Argument order is `(x, y)` — not `(y, x)`.** |
| `sinh` | `sinh(x) -> float` | Hyperbolic sine. `x` is a float. |
| `cosh` | `cosh(x) -> float` | Hyperbolic cosine. |
| `tanh` | `tanh(x) -> float` | Hyperbolic tangent. |
| `fact` | `fact(n) -> int` | n! (n ≥ 0). |
| `perm` | `perm(n, k) -> int` | n!/(n-k)! — ordered selections. |
| `binom` | `binom(n, k) -> int` | C(n, k) — unordered selections. |
| `gcd` | `gcd(a, b) -> int` | Greatest common divisor. |
| `lcm` | `lcm(a, b) -> int` | Least common multiple. |
| `even` | `even(n) -> bool` | Parity check; passable as a callback. |
| `odd` | `odd(n) -> bool` | Parity check; passable as a callback. |
| `rem` | `rem(a, b) -> num` | Remainder; **same sign as `a`**, magnitude < |b|. |
| `rem-euclid` | `rem-euclid(a, b) -> num` | Remainder; **always non-negative**, in `[0, |b|)`. |
| `div-euclid` | `div-euclid(a, b) -> num` | Quotient that pairs with `rem-euclid`. Rounds toward `-inf`. |
| `quo` | `quo(a, b) -> int` | Floored integer division; always returns `int`. |
| `norm` | `norm(p: 2.0, ..vs) -> float` | L^p norm of values. Default p = 2 (Euclidean). |

### Constants

| Name | Value |
|---|---|
| `calc.pi` | π ≈ 3.14159… |
| `calc.tau` | 2π ≈ 6.28318… |
| `calc.e` | Euler's e ≈ 2.71828… |
| `calc.inf` | Floating-point positive infinity. |

---

## Worked examples (compile-verified)

| Topic | File |
|---|---|
| `abs`, `min`, `max`, `clamp` | [`01-arith-basics.typ`](./examples/06-calc/01-arith-basics.typ) |
| `floor`, `ceil`, `trunc`, `fract`, `round` (with `digits:`) | [`02-rounding.typ`](./examples/06-calc/02-rounding.typ) |
| `pow`, `sqrt`, `root`, `exp`, `log` (with `base:`), `ln` | [`03-powers-roots-logs.typ`](./examples/06-calc/03-powers-roots-logs.typ) |
| `sin`/`cos`/`tan`, `asin`/`acos`/`atan`/`atan2`, `sinh`/`cosh`/`tanh` | [`04-trig.typ`](./examples/06-calc/04-trig.typ) |
| `fact`, `perm`, `binom`, `gcd`, `lcm`, `even`, `odd` (as filter cb) | [`05-integers.typ`](./examples/06-calc/05-integers.typ) |
| `rem`, `rem-euclid`, `div-euclid`, `quo` (sign-handling differences) | [`06-division.typ`](./examples/06-calc/06-division.typ) |
| `norm` with `p:`, constants `pi`/`tau`/`e`/`inf` | [`07-norm-and-constants.typ`](./examples/06-calc/07-norm-and-constants.typ) |

---

## Pitfalls (agent-targeted)

1. **`calc.` prefix is mandatory.** Bare `sin(...)` is not defined. Always `calc.sin(...)`.
2. **`atan2(x, y)`, not `atan2(y, x)`.** Opposite of most languages. Easy to invert.
3. **Trig with bare numbers means radians.** `calc.sin(90)` is `sin(90 rad)`, not `sin(90°)`. Use the `90deg` literal for degrees.
4. **`round` returns the input's numeric type.** `calc.round(3.5) -> float` (`4.0`), not int. Wrap in `int(...)` if you need `int`.
5. **`round` half-rounding is AWAY from zero**, not banker's rounding. `round(2.5) = 3`, `round(-2.5) = -3`.
6. **`sqrt(x)` requires `x >= 0`** — negative input is a hard error. Use `root(x, n)` with odd `n` for negative inputs.
7. **`rem` vs `rem-euclid`.** For modular arithmetic on possibly-negative inputs, you almost always want `rem-euclid` (always non-negative). `rem` matches the C/Rust `%` operator.
8. **`fact(n)` is a real factorial** — overflows hit fast. `fact(21)` already exceeds int64. Use `decimal` arithmetic if you need bigger.
9. **`min`/`max` work on strings too**, ordering lexicographically. Mixing types (e.g. `min(1, "x")`) errors.

---

## Self-check

1. Did you prefix every call with `calc.` ?
2. For trig: angles in `deg` or numbers in radians — are you using the form you intended?
3. For modular arithmetic on signed inputs: do you want `rem` (sign of dividend) or `rem-euclid` (always ≥ 0)?
4. For `round`, do you actually want the SAME type back, or do you need `int(round(...))`?
5. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
