# `table` — tabular data

`table(..children: content, columns: track-spec, rows: track-spec, gutter: track-spec, column-gutter: track-spec, row-gutter: track-spec, inset: ?, align: ?, fill: ?, stroke: ?) -> content`

Arranges content in cells, in **row-major order**. Shares its core mechanics with `grid` but with **table-friendly defaults** (visible 1pt black `stroke`, `5pt` `inset`).

```typst
#table(
  columns: 4,
  table.header([], [Q1], [Q2], [Q3]),
  [Revenue], [1k], [2k], [3k],
  [Profit],  [.5k], [1k], [1.5k],
)
```

## When to use `table` vs `grid`

| Concern                    | Use         |
| -------------------------- | ----------- |
| Related data points (semantic table) | `table` |
| Just a layout grid (e.g. side-by-side images) | `grid` |
| Screen reader should announce "table" | `table` |
| You want visible cell borders by default | `table` (already on) |

## Track sizing

`columns` / `rows` accept:

| Spec     | Meaning                                                        |
| -------- | -------------------------------------------------------------- |
| `int`    | That many `auto` tracks                                         |
| `auto`   | Size to content                                                  |
| Length   | Fixed (`100pt`, `2cm`, `30%`)                                    |
| Fraction | `1fr`, `2fr` — share remaining space                              |
| Array    | One entry per track: `(1fr, auto, 100pt)`                       |

## Per-cell function form

`fill`, `align`, `inset`, `stroke` accept a function `(x, y) -> value` where `x` = column index, `y` = row index (0-based):

```typst
#table(
  fill: (x, _) => if calc.odd(x) { luma(240) } else { white },
  align: (x, y) => if y == 0 { center } else if x == 0 { left } else { right },
  ...
)
```

## `table.cell` — per-cell overrides + spans

```typst
table.cell(
  body,
  x: auto, y: auto,
  colspan: 1, rowspan: 1,
  inset: auto, align: auto, fill: auto, stroke: (:),
  breakable: auto,
)
```

Most powerful uses: `colspan` / `rowspan` to merge cells, plus per-cell style overrides without relying on positional rules.

You can also `#show table.cell.where(...): ...` to apply rules across selected cells:

```typst
#show table.cell.where(y: 0): strong   // bold the header row
#show table.cell.where(x: 0): strong   // bold the first column
```

## `table.header` and `table.footer`

Wrap the leading rows in `table.header(...)` so:

1. AT (screen readers) announces them as column headers.
2. They **repeat on every page** the table breaks across (set `repeat: false` to disable).

`table.footer(...)` works analogously and goes at the END (no other cells after it).

`level:` on a header lets you stack multiple repeating headers; only the highest still in scope repeats.

## `table.hline` / `table.vline`

Manual lines that:

- Override per-cell strokes (use `stroke: none` to *remove* a line where one would otherwise be).
- Cross gutter spacing (per-cell strokes can't).

```typst
table.hline(y: 2, start: 1, end: 3, stroke: 0.7pt + gray, position: top)
table.vline(x: 1, stroke: red, position: start)
```

## Captioning + referencing

Tables themselves are NOT directly referenceable. Wrap in a `figure` to get a caption + counter + `@ref`:

```typst
#figure(
  table(...),
  caption: [Timing],
) <timing>
@timing
```

`figure` auto-detects the `table` kind and uses the table counter.

## Pitfalls

- **Children are positional and consumed row-major.** `table(columns: 3, [a], [b], [c], [d])` puts `d` alone on a second row.
- **`table.header` is not optional for accessibility.** Even tables that fit on one page should mark their header rows so AT announces column labels.
- **Per-cell stroke vs `table.hline`.** Per-cell strokes don't cross gutter; `hline`/`vline` do. Choose based on whether your design uses gutters.
- **Set rules on `table` don't affect `grid`** and vice versa, even though they share most parameters.
- **`stroke: none`** disables ALL borders, including those between cells. Use a per-side dictionary (e.g. `stroke: (top: 0.7pt, bottom: 0.7pt)`) if you only want some sides.
- **Alignment functions get `(x, y)` not `(col, row)`.** They are the same thing, but if you imported old grid code calling them by other names, the order is `x` first.
- **Setting `gutter: 0pt`** doesn't fully remove gaps when individual `column-gutter` / `row-gutter` are set — they take precedence.

## Examples (compile-verified)

- `examples/18-table/01-basics.typ` — fixed columns + header, mixed-size columns (`1fr, auto, auto`) with `inset` and `align: horizon`.
- `examples/18-table/02-fill-and-align-functions.typ` — striped `fill: (x, _) => ...`, `align: (x, y) => ...`, per-side `inset` dict.
- `examples/18-table/03-cell-spans-hlines-vlines.typ` — `import table: cell, header, footer`, `colspan`, header + footer, manual `table.hline` placement.

## Reference

- Official: https://typst.app/docs/reference/model/table/
- Table Guide: https://typst.app/docs/guides/tables/
- `grid` (sibling element): https://typst.app/docs/reference/layout/grid/
- `figure` (for captions + referencing): https://typst.app/docs/reference/model/figure/
- `stroke`: https://typst.app/docs/reference/visualize/stroke/
