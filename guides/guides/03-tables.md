# Tables Guide

Tables in Typst are produced by [`table(...)`](../reference/model/13-table.md).
A table is a sequence of cells laid out in a grid, with explicit
column tracks and (optional) row tracks. This guide covers everything
from the smallest two-cell sketch to fully accessible, multi-page,
header-and-footer tables ready for PDF/UA.

## Anatomy

```typst
#table(
  columns: (auto, auto, auto),
  table.header[Name][Score][Grade],   // sticky header row(s)
  [Alice], [92], [A],
  [Bob],   [76], [C],
  [Carol], [88], [B],
  table.footer[3 students surveyed],  // sticky footer row(s)
)
```

Every cell is a positional argument. Typst fills the grid
**row-major** — the cell sequence advances column by column, then
moves to the next row when it has filled the column count.

## Column tracks

The `columns` parameter is the spec. Each entry is one column track:

| Spec        | Meaning                                              |
| ----------- | ---------------------------------------------------- |
| `auto`      | As wide as the widest cell in the column.            |
| `<length>`  | Fixed width: `2cm`, `1.5in`, `30pt`.                 |
| `<ratio>`   | Fraction of the *available* width: `25%`.            |
| `<fraction>`| Share of the *remaining* width: `1fr`, `2fr`.        |

Common patterns:

```typst
columns: 3                        // three auto-sized columns
columns: (auto, 1fr, 1fr)         // first auto, rest split equally
columns: (1cm, 2cm, auto)         // fixed two, then auto
columns: 4 * (1fr,)               // four equal-fraction columns
```

`rows` works identically (default `auto`).

## Cell content vs `table.cell`

The simplest cells are bare content (`[A]`, `[2cm]`, etc.). For
per-cell overrides — colspan, rowspan, alignment, fill, padding,
stroke — wrap with `table.cell(...)`:

```typst
table.cell(colspan: 2)[Spans two columns]
table.cell(rowspan: 3, fill: aqua)[Spans three rows]
table.cell(align: right)[123.45]
```

Common `table.cell` parameters:

| Parameter | Effect                                      |
| --------- | ------------------------------------------- |
| `colspan` | Span this many columns.                     |
| `rowspan` | Span this many rows.                        |
| `align`   | Per-cell alignment (overrides table-wide).  |
| `fill`    | Background color.                           |
| `inset`   | Padding inside the cell.                    |
| `stroke`  | Per-cell border.                            |
| `breakable`| Allow splitting across pages (default `auto`). |

## Sticky headers and footers

`table.header(...)` and `table.footer(...)` mark rows that **repeat
on every page** the table spans, and that are tagged as semantic
header/footer rows (important for accessibility):

```typst
#table(
  columns: 3,
  table.header[Name][Q1][Q2],
  ..for r in data { (r.name, str(r.q1), str(r.q2)) },
  table.footer[Total][#total-q1][#total-q2],
)
```

Headers can be multi-row by passing more cells. Each row is
`columns`-many cells.

## Alignment, stroke, and inset (whole-table)

Set defaults at the table level — they propagate to every cell that
doesn't override them:

```typst
#table(
  columns: 4,
  align: (left, center, right, right),    // per-column
  stroke: 0.5pt + gray,                   // every border
  inset: 6pt,
  ...
)
```

Per-side stroke is a dictionary:

```typst
stroke: (top: 1pt, bottom: 1pt, x: none)   // ruled top/bottom only
```

To remove a single border, set its side to `none`. To override a
*per-cell* border, use `table.cell(stroke: ...)`.

`inset` is shorthand for cell padding; pass a dict for asymmetric
padding (`(x: 8pt, y: 4pt)`).

## Striping rows or columns (`fill`)

`fill` accepts content (a color, gradient, tiling) **or a function**.
Functions give you per-cell control:

```typst
#table(
  columns: 3,
  fill: (col, row) => if calc.even(row) { silver.lighten(70%) },
  ...
)
```

The function receives `(column_index, row_index)` and returns a
color (or `none` for no fill). Use `calc.odd`/`calc.even` for
alternating row stripes.

## Multi-page tables

Tables break naturally between pages. Combined with `table.header`
the header repeats automatically. You can pin extra rows to the top
of every page chunk by passing them inside the header — `table.header`
takes any number of cells.

For a header that should *not* repeat, pass `repeat: false`:

```typst
table.header(repeat: false, [Top-of-table label])[col 1][col 2][col 3]
```

## Spanning cells: `colspan` / `rowspan`

```typst
#table(
  columns: 4,
  table.cell(colspan: 4)[Quarterly report],
  table.cell(rowspan: 2, fill: aqua)[Q1],
  [Jan], [Feb], [Mar],
  [10],  [20],  [30],
)
```

`rowspan` cells take their slot from the **first** row they appear
in; the cells in subsequent rows shift accordingly. Typst does the
bookkeeping for you.

## Captions: wrap in a `figure`

`table` itself has no caption parameter. Wrap with
[`figure(...)`](../reference/model/06-figure.md) for captions,
labels, and cross-references:

```typst
#figure(
  table(
    columns: 2,
    table.header[Item][Price],
    [Bread], [\$3.50],
    [Milk],  [\$2.75],
  ),
  caption: [Grocery prices in USD.],
) <prices>

See @prices for details.
```

## Quick recipe library

### Striped, ruled

```typst
#table(
  columns: 3,
  align: (left, right, right),
  stroke: (top: 0.7pt, bottom: 0.7pt, x: none),
  fill: (_, row) => if calc.odd(row) and row > 0 { silver.lighten(70%) },
  table.header[Name][Q1][Q2],
  [Alice], [12], [15],
  [Bob],   [9],  [14],
  [Carol], [17], [11],
)
```

### Borderless, just spacing

```typst
#table(
  columns: 3, stroke: none, inset: 8pt,
  ..rows.flatten(),
)
```

### Compact comparison (key/value)

```typst
#table(
  columns: 2, stroke: none, inset: (x: 6pt, y: 3pt),
  align: (right, left),
  [*Title*], [A Fluid Dynamic Model],
  [*Authors*], [Tungsten, Deklan],
  [*Year*], [2026],
)
```

## Accessibility (PDF/UA, screen readers)

A table that just *looks* tabular isn't accessible. Five principles:

1. **Use `table`, not `grid`,** for tabular data. Only `table` is
   exposed as a table to assistive technology (AT).
2. **Use `table.header`** for the column-label row(s). They will be
   announced when AT enters a data cell.
3. **For row-headers** (the leftmost column labels each row), wrap
   each header cell with `pdf.header-cell(scope: "row")`. (Requires
   the `a11y-extras` feature flag today; see
   [`pdf.header-cell`](../reference/pdf/04-header-cell.md).)
4. **For corner cells** (top-left labelling both row and column) use
   `pdf.header-cell(scope: "both")`.
5. **For complex tables**, wrap in
   [`pdf.table-summary`](../reference/pdf/05-table-summary.md) with
   instructions to help AT users navigate. Don't duplicate visual
   content — describe *structure*.

Avoid:

- Empty header cells (use a non-empty placeholder or `pdf.header-cell`
  with `scope: "row"` if it's a row label).
- Cells whose meaning depends on layout (e.g. a single colored cell
  that means "warning"). Add explicit text or alt text via a figure.
- Skipping `table.header` and styling the first row to *look* like a
  header. AT cannot recover the semantic from styling.

See the [accessibility guide](./04-accessibility.md) for the broader
picture and the [PDF module pages](../reference/pdf/00-pdf-overview.md)
for tag-specific overrides.

## Performance tips

- Prefer **fixed or fractional column widths** over `auto` for very
  large tables — Typst doesn't have to measure every cell.
- For huge tables (thousands of rows), generate cells in a
  comprehension rather than a literal: build an array, then spread
  it: `..rows.flatten()`.
- Heavy per-cell strokes are expensive. Use `stroke: (top: ..., bottom: ...)`
  on the table and let cells inherit.
