# `math.cases(..children, delim: ("{", "}"), reverse: false, gap: 0.2em)` — case distinction

Renders a piecewise / case-distinction expression with a left brace by default. Each argument is one branch; align across branches with `&`.

## Parameters

| Param      | Type                                  | Default          | Notes                                                                  |
| ---------- | ------------------------------------- | ---------------- | ---------------------------------------------------------------------- |
| `delim`    | str / array / symbol / `none`         | `("{", "}")`      | Single char = left delimiter (right inferred). Pair = explicit both.  |
| `reverse`  | bool                                  | `false`           | Put the delimiter on the right side of the cases instead of the left. |
| `gap`      | relative                              | `0.2em`           | Vertical gap between branches.                                         |
| `children` | content (variadic)                    | required         | The branches.                                                          |

## Examples (compile-verified)

- `examples/05-cases/01-cases.typ` — standard piecewise, alignment with `&`, custom delimiter, `reverse`, wider `gap`.

## Reference

https://typst.app/docs/reference/math/cases/
