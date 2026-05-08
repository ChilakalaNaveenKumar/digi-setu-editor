# `math.mat` — matrix

Renders a matrix. Inside math calls, `,` separates **columns** and `;` separates **rows**.

## Parameters

| Param         | Type                                  | Default        | Notes                                                                                |
| ------------- | ------------------------------------- | -------------- | ------------------------------------------------------------------------------------ |
| `delim`       | str / array / symbol / `none`        | `("(", ")")`   | Single char = left delimiter (right inferred). Pair = explicit both.                |
| `align`       | alignment                              | `center`        | Horizontal alignment of each cell.                                                   |
| `augment`     | `none` / int / dictionary             | `none`          | Partition lines (see below).                                                         |
| `gap`         | relative                               | `0pt`           | Shorthand: sets both `row-gap` and `column-gap`.                                    |
| `row-gap`     | relative                               | `0.2em`         | Vertical gap between rows.                                                           |
| `column-gap`  | relative                               | `0.5em`         | Horizontal gap between columns.                                                      |
| `rows`        | content (variadic, 2-D via `;`)       | required       | The matrix content.                                                                  |

## `augment` — partition lines

| Form          | Effect                                                                                          |
| ------------- | ----------------------------------------------------------------------------------------------- |
| `2`            | One vertical line after column 2.                                                              |
| `-1`           | One vertical line after the column counted from the end (so `... | last`).                     |
| Dictionary    | Full control: `(hline: int / array, vline: int / array, stroke: <stroke>)`. `auto` stroke = 0.05em squared caps. |

```typst
$ mat(1, 0, 1; 0, 1, 2; augment: #2) $
$ mat(0, 0, 0; 1, 1, 1; augment: #(hline: 1, stroke: 2pt + green)) $
```

## Building from data

`mat()` is a normal math function — you can pass arrays via `..` spread:

```typst
#let data = ((1, 2, 3), (4, 5, 6))
$ mat(..data) $                          // each inner array becomes a row

$ mat(..#range(1, 5).chunks(2)) $        // ((1, 2), (3, 4))
```

## Aligning across rows

Use `&` inside cells in the same row to align — same idea as in `cases`.

## Examples (compile-verified)

- `examples/10-mat/01-mat-basics.typ` — basic matrix, `delim`, `align: right`, `row-gap`, `column-gap`.
- `examples/10-mat/02-mat-augment-and-spread.typ` — `augment` integer + dictionary, building from data, `..#range(...).chunks(...)` spread.

## Reference

https://typst.app/docs/reference/math/mat/
