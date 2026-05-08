# `pdf.header-cell` – Force a Cell to be a *Header* Cell

```typst
pdf.header-cell(
  level: int,
  scope: "column" | "row" | "both",
  cell,
) -> content
```

Marks `cell` as a **header cell** so AT can announce it as a label
when the user navigates into a related row, column, or both. Use it
in three situations the default classification can't cover:

1. **Row headers** — the leftmost column labels each row. Pass
   `scope: "row"`.
2. **Corner cells** that label both the row *and* the column they
   sit at the intersection of. Pass `scope: "both"`. (Typically the
   top-left cell of a `table.header(...)`.)
3. **Header cells outside `table.header(...)`** — useful for
   sub-headers in a row that's otherwise data.

## Defaults that already work

- Cells inside `table.header(...)` are **header cells with
  `scope: "column"`** — they label every cell in their column. You
  don't need `pdf.header-cell` for those.
- Use the `level:` parameter on `table.header(...)` itself to mark a
  header that's labelled by another higher-level header.

Reach for `pdf.header-cell` only for the cases above.

## Feature flag

Behind the `a11y-extras` flag today:

```bash
typst compile paper.typ --features a11y-extras
```

The API may move out of `pdf.` (so HTML export can use the same
metadata). Functionality is here to stay.

## Parameters

| Name    | Type                       | Default     | Notes                                         |
| ------- | -------------------------- | ----------- | --------------------------------------------- |
| `level` | int                        | `1`         | Nesting level of this header.                 |
| `scope` | `"column"` / `"row"` / `"both"` | `"column"` | What track of the table this header labels. |
| `cell`  | content / `table.cell(...)`| —           | The cell.                                     |

## Recipe – nutrition table with a row-header column

```typst
#table(
  columns: 3,
  align: (start, end, end),

  table.header(
    pdf.header-cell(scope: "both")[Nutrient],   // labels rows AND columns
    [Per 100g],
    [Per Serving],
  ),

  pdf.header-cell(scope: "row")[Calories], [250 kcal], [375 kcal],
  pdf.header-cell(scope: "row")[Protein],  [8g],       [12g],
  pdf.header-cell(scope: "row")[Fat],      [12g],      [18g],
  pdf.header-cell(scope: "row")[Carbs],    [30g],      [45g],
)
```

When AT navigates a data cell like `[12g]`, the user can ask for
the headers — they'll hear "Protein" (the row header) and
"Per 100g" (the column header).

## When you don't need this

- A purely top-row column-labels table — `table.header(...)` alone
  is enough.
- A table whose first column happens to be bold but isn't actually
  labelling rows (e.g. the first column is a name, not a category).
- A `grid` — `pdf.header-cell` only applies inside `table`.
