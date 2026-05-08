# `angle` (type) — rotation magnitude

Numeric type representing an angle.

## Units

| Unit  | Notation     | Notes                                |
| ----- | ------------ | ------------------------------------ |
| `deg`  | `180deg`      | Degrees                              |
| `rad`  | `3.14rad`     | Radians (`calc.pi rad ≈ 180deg`)     |

## Methods

| Method   | Returns          |
| -------- | ---------------- |
| `deg()`   | Convert to a `float` of degrees  |
| `rad()`   | Convert to a `float` of radians  |

## Arithmetic

Angles support `+`, `-`, multiplication by int/float, division.

```typst
#(45deg + 30deg)        // 75deg
#(2 * 45deg)            // 90deg
```

## Where they're used

`rotate(angle: ...)`, `skew(ax: ..., ay: ...)`, `stretch(...)`, `place(...)`, `path(...)` for tangents/curves.

## Examples (compile-verified)

- `examples/03-angle/01-angle.typ` — literal angles, conversions, arithmetic, batch rotation in a stack.

## Reference

https://typst.app/docs/reference/layout/angle/
