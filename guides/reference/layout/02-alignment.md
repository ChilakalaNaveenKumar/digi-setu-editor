# `alignment` (type) — position along an axis

Type used wherever Typst expects an alignment (`align()`, `place()`, `mat(align: ...)`, etc.).

## Values

| Value     | Axis        | Behaviour                                     |
| --------- | ----------- | --------------------------------------------- |
| `start`    | horizontal  | Logical start (follows text direction)        |
| `end`      | horizontal  | Logical end                                    |
| `left`     | horizontal  | Absolute left                                  |
| `center`   | horizontal  | Middle                                         |
| `right`    | horizontal  | Absolute right                                 |
| `top`      | vertical    | Top                                            |
| `horizon`  | vertical    | Middle                                         |
| `bottom`   | vertical    | Bottom                                         |

These names are available **globally** AND inside the `alignment` scope:
`center` ≡ `alignment.center`. The unqualified form is the conventional one.

## Combining axes

Add a horizontal and a vertical alignment with `+`:

```typst
#align(top + right)[corner]
```

The result is itself a 2-D `alignment`.

## Fields

| Field | Notes                                                              |
| ----- | ------------------------------------------------------------------ |
| `x`   | Horizontal component (or `none` if 1-D vertical).                  |
| `y`   | Vertical component (or `none` if 1-D horizontal).                  |

## Methods

| Method      | Returns                                                                  |
| ----------- | ------------------------------------------------------------------------ |
| `axis()`    | `"horizontal"`, `"vertical"`, or `none` for 2-D alignments              |
| `inv()`     | The inverse: `top → bottom`, `left → right`, `center → center`, ...     |

## Examples (compile-verified)

- `examples/02-alignment/01-alignment-type.typ` — equivalent forms, `.x`/`.y` field access, `axis()`, `inv()`.

## Reference

https://typst.app/docs/reference/layout/alignment/
