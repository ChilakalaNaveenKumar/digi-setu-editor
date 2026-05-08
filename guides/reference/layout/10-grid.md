# `grid` — arrange content in a 2-D track grid

Lays out content in cells across rows and columns. **Same core API as `table`** but with different semantics: grids are for **layout** only, tables for **data**. AT (screen readers) reads grids in order; tables get the cell-navigation semantics.

## Track sizing values

Each entry in `columns` / `rows` / `gutter` arrays can be:

| Value          | Behaviour                                                                       |
| -------------- | ------------------------------------------------------------------------------- |
| `auto`          | Fits content; if multiple `auto` tracks compete for space, distributes fairly. |
| length / relative | Fixed (`60pt`, `30%`, `20% - 4pt`).                                            |
| `1fr`           | Shares **remaining** space proportionally with other fractional tracks.         |

Shorthands:

| Form                | Equivalent                                  |
| ------------------- | ------------------------------------------- |
| `columns: 3`        | `columns: (auto, auto, auto)`                |
| `rows: ()`          | All extra rows are `auto`                    |
| `gutter: 5pt`       | Sets both `column-gutter` and `row-gutter` |

## Top-level parameters

| Param           | Type                                | Default | Notes                                                            |
| --------------- | ----------------------------------- | ------- | ---------------------------------------------------------------- |
| `columns`       | int / array of sizes                | `()`    | Column tracks.                                                    |
| `rows`          | int / array of sizes                | `()`    | Row tracks (extras default to `auto`).                            |
| `gutter`        | size / array                         | `()`    | Both gutters at once.                                            |
| `column-gutter` | size / array                         | `()`    | Gap between columns.                                              |
| `row-gutter`    | size / array                         | `()`    | Gap between rows.                                                |
| `inset`         | length / dict / array / function    | `(:)`   | Cell padding.                                                    |
| `align`         | alignment / array / function         | `auto`  | Cell content alignment.                                          |
| `fill`          | color / gradient / array / function | `none`  | Cell background.                                                 |
| `stroke`        | stroke spec / array / function       | `none`  | Cell borders.                                                    |

The "per-cell" fields (`inset`, `align`, `fill`, `stroke`) accept three shapes:

1. A **single value** applied uniformly.
2. An **array** cycled across columns.
3. A **function** `(x, y) => value` taking 0-based column / row indices.

## Sub-elements

| Element        | Purpose                                                       |
| -------------- | ------------------------------------------------------------- |
| `grid.cell`     | Per-cell override (colspan, rowspan, fill, align, inset, stroke, x, y) |
| `grid.hline`    | Manual horizontal line at a row position                       |
| `grid.vline`    | Manual vertical line at a column position                      |
| `grid.header`   | Header rows (repeat across pages)                             |
| `grid.footer`   | Footer rows (repeat across pages)                             |

## Stroke precedence (when conflicting)

`hline`/`vline` > `cell` > top-level `grid`.

## Grid vs Table — quick reference

| Aspect              | `grid`                                  | `table`                                 |
| ------------------- | --------------------------------------- | --------------------------------------- |
| Intended for        | Visual layout                            | Tabular data                             |
| Default `stroke`     | None                                     | Lines visible                           |
| Default `inset`      | None                                     | `5pt`                                   |
| AT semantics        | Just a visual arrangement               | Rows / columns navigable                 |

## Examples (compile-verified)

- `examples/10-grid/01-grid-basics.typ` — mixed `(60pt, 1fr, 2fr)` columns, colspan, spreading an array of strings.
- `examples/10-grid/02-grid-styling-and-cells.typ` — per-cell array/function styling, header/footer with manual lines, header bold show rule.

## Reference

https://typst.app/docs/reference/layout/grid/
