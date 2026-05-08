# `pdf.table-summary` – AT-Only Summary for a Complex Table

```typst
pdf.table-summary(summary: str, table) -> content
```

Wraps a `table` with a structural **summary** that's exposed only to
AT — *not* shown to sighted readers. Use it when the table's layout
is non-trivial (spanning cells, multi-level headers, repeated
sub-tables) and AT users would benefit from "directions" before
diving in.

## What goes in `summary`

- **Structural orientation.** "The first two columns list names; the
  third column groups members into teams using rowspans."
- **Navigation hints.** "Read top-to-bottom, left-to-right; team
  groupings are not in alphabetical order."
- **Header semantics.** "The bold row at the top is a column
  header; the bold cell at the start of each section is a sub-header."

What does **not** belong in `summary`:

- The table's **content**. AT users can already navigate it cell by
  cell.
- The table's **conclusion / takeaway**. Put that in the figure
  `caption:` (visible to everyone) instead.
- Anything that would be useful to sighted readers — make that
  visible.

If you can't think of structural information beyond "it's a table",
you don't need a summary.

## Feature flag

Behind the `a11y-extras` flag today:

```bash
typst compile paper.typ --features a11y-extras
```

The wider API may move out of `pdf.` in the future, but the summary
will remain a PDF-only concept (HTML has its own
`<table summary="..">`-style affordances).

## Parameters

| Name      | Type          | Required | Notes                                                 |
| --------- | ------------- | -------- | ----------------------------------------------------- |
| `summary` | str           | yes      | The summary text (plain string; no markup).           |
| `table`   | content       | yes      | The table (a call to `table(...)`).                   |

## Recipe – complex grouping table

```typst
#figure(
  pdf.table-summary(
    summary: "The first two columns list participants. The third column "
            + "uses rowspans to assign each contiguous group of "
            + "participants to one team.",
    table(
      columns: 3,
      table.header[First Name][Given Name][Group],
      [Mike], [Davis], table.cell(rowspan: 3)[Sales],
      [Anna], [Smith],
      [John], [Johnson],
      [Sara], [Wilkins], table.cell(rowspan: 2)[Operations],
      [Tom],  [Brown],
    ),
  ),
  caption: [The Sales org now has a new member.],
)
```

The summary helps AT users understand they're walking through
*group-by-rowspan*, while the visible caption captures the actual
takeaway.

## When to skip

- Simple tables with one column-label row → no summary needed.
- Tables whose only "complexity" is striping or borders → no summary.
- Tables that already have a clear caption explaining structure → no
  summary; the caption is better because everyone benefits.
