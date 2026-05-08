# `math.vec(..children, delim: ("(", ")"), align: center, gap: 0.2em)` — column vector

Renders a column vector (vertically stacked elements with delimiters).

## Parameters

| Param      | Type                                  | Default          | Notes                                                                       |
| ---------- | ------------------------------------- | ---------------- | --------------------------------------------------------------------------- |
| `delim`    | str / array / symbol / `none`         | `("(", ")")`     | Single char = left delimiter (right inferred). Pair = explicit both.       |
| `align`    | alignment                              | `center`         | Horizontal alignment of each element.                                       |
| `gap`      | relative                               | `0.2em`          | Vertical gap between elements.                                              |
| `children` | content (variadic)                    | required         | The vector elements.                                                        |

## When NOT to use `vec`

`vec` is for the **components** of a vector. To typeset a single **symbol** that represents a vector (so it can mix into formulas like a variable), use `arrow(v)` or `bold(v)` instead.

```typst
$ arrow(v) = vec(v_1, v_2, v_3) $
```

## Examples (compile-verified)

- `examples/19-vec/01-vec.typ` — standard column vector, custom `delim`, right-`align`, wider `gap`, vector symbols vs components.

## Reference

https://typst.app/docs/reference/math/vec/
