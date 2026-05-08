# `int` — 64-bit signed integers

A whole number stored as a 64-bit signed integer.

- Range: `-9223372036854775808 ..= 9223372036854775807`.
- Integer **literals** are always non-negative; `-1` is parsed as the negation operator applied to the literal `1`.
- A literal that exceeds the max (or `<= -2^63`) is parsed as a `float`. To get exactly `i64::MIN`, do it via arithmetic: `-9223372036854775807 - 1`.
- Bases:
  - decimal — `42`
  - hexadecimal — `0xff`
  - octal — `0o10`
  - binary — `0b1001`

## Constructor

`int(value)` converts to `int`:

| Input     | Behavior                                          |
| --------- | ------------------------------------------------- |
| `bool`    | `false → 0`, `true → 1`                           |
| `float`   | truncate **toward zero** (`2.7 → 2`, `-2.7 → -2`) |
| `decimal` | truncate **toward zero**                          |
| `str`     | parse as base 10; non-numeric strings error       |
| `int`     | identity                                          |

> Truncation toward zero is **not** the same as `calc.floor` (which rounds toward `-∞`). For negatives the two disagree.

## Methods

All called as `value.method(...)`. Bitwise methods treat the operand as a signed 64-bit integer.

| Method                         | Returns | Notes                                                                |
| ------------------------------ | ------- | -------------------------------------------------------------------- |
| `.signum()`                    | `int`   | `-1`, `0`, or `+1`                                                   |
| `.bit-not()`                   | `int`   | bitwise NOT                                                          |
| `.bit-and(rhs)`                | `int`   |                                                                      |
| `.bit-or(rhs)`                 | `int`   |                                                                      |
| `.bit-xor(rhs)`                | `int`   |                                                                      |
| `.bit-lshift(shift)`           | `int`   | errors if it overflows 64 bits; `shift` must be `≥ 0`                |
| `.bit-rshift(shift, logical:)` | `int`   | **arithmetic** by default (sign-extends); `logical: true` for unsigned |
| `.to-bytes(endian:, size:)`    | `bytes` | defaults: `endian: "little"`, `size: 8`                              |

### Static (associated) methods

- `int.from-bytes(b, endian: "little"|"big", signed: bool) -> int`
  - `b.len() <= 8` required.
  - With `signed: true` (default), the high bit is the sign bit. With `signed: false` the result is non-negative.

## Pitfalls / gotchas

- **Method on a negative literal needs parens**: `(-5).signum()`, not `-5.signum()` (the latter is `-(5.signum())`).
- **`int(2.7)` ≠ `calc.floor(2.7)` for negatives**: `int(-2.7) == -2`, `calc.floor(-2.7) == -3`.
- **`bit-lshift` can overflow**; `bit-rshift` saturates instead and never errors.
- **`to-bytes` with too-small `size`** silently truncates; for negative numbers the truncated bytes can round-trip to a different (positive) value because the sign bit is dropped.
- **Endianness**: the *default* for `to-bytes` / `from-bytes` is `"little"`. If you're moving bytes through formats that assume big-endian (most network protocols), set `endian: "big"` explicitly.

## Examples (compile-verified)

- `examples/15-int/01-literals-and-construct.typ` — literals in 4 bases; `int()` from every supported input type.
- `examples/15-int/02-signum-and-bitops.typ` — `signum`, every `bit-*` op, arithmetic vs logical right shift.
- `examples/15-int/03-bytes-roundtrip.typ` — `to-bytes` / `from-bytes` with `size`, `endian`, `signed`.

## Reference

- Official: https://typst.app/docs/reference/foundations/int/
