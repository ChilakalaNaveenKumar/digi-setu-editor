# `pdf.data-cell` – Force a Cell to be a *Data* Cell

```typst
pdf.data-cell(cell) -> content
```

Each cell in a `table` is either a **header cell** or a **data
cell**. By default:

- Cells inside [`table.header(...)`](../model/13-table.md#header) → header.
- All other cells → data.

If a cell inside `table.header` is *not* really a header (for
example a status indicator that happens to live in the header row),
mark it as a data cell with `pdf.data-cell` so that AT classifies it
correctly.

## Feature flag

This function is currently behind the `a11y-extras` feature flag:

```bash
typst compile paper.typ --features a11y-extras
```

The API may move out of `pdf.` in a future release (so that other
export targets can use the same metadata). The functionality itself
is here to stay.

## Parameters

| Name   | Type                       | Required | Notes                                                |
| ------ | -------------------------- | -------- | ---------------------------------------------------- |
| `cell` | content or `table.cell(...)` | yes    | The cell to mark as data.                            |

## Recipe

OKR table where each "objective" header row also carries a status
indicator that should be treated as data, not as part of the column
header set:

```typst
#table(
  columns: 3,
  align: (left, left, center),

  table.header[Objective][Key Result][Status],

  table.header(
    level: 2,
    table.cell(colspan: 2)[Improve Customer Satisfaction],
    pdf.data-cell[✓ On Track],          // status is data, not a header
  ),
  [], [Increase NPS to 50+], [45],
  [], [Reduce churn to <5%], [4.2%],
)
```

Without `pdf.data-cell`, the "✓ On Track" cell would inherit the
header semantics of `table.header(level: 2, ...)` — wrong from an
AT perspective.

## When you don't need this

If your header row contains only column labels, you don't need
`pdf.data-cell` at all — the default classification is correct.
Reach for it only when you have *non-label content* sitting inside a
`table.header(...)` block.
