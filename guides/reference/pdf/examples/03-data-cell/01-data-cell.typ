// NOTE: Requires the `a11y-extras` feature flag:
//   typst compile --features a11y-extras 01-data-cell.typ
//
// Without the flag, this file will fail to compile with an error
// telling you to enable it.

#set page(width: 14cm, height: auto, margin: 1cm)

#show table.cell.where(x: 0): set text(weight: "bold")
#show table.cell.where(x: 1): set text(style: "italic")
#show table.cell.where(x: 1, y: 0): set text(style: "normal")

#table(
  columns: 3,
  align: (left, left, center),

  table.header[Objective][Key Result][Status],

  table.header(
    level: 2,
    table.cell(colspan: 2)[Improve Customer Satisfaction],
    // This sits inside `table.header(...)` but is NOT a header cell —
    // it's a status value, so we mark it as data.
    pdf.data-cell[✓ On Track],
  ),
  [], [Increase NPS to 50+], [45],
  [], [Reduce churn to \<5%], [4.2%],

  table.header(
    level: 2,
    table.cell(colspan: 2)[Grow Revenue],
    pdf.data-cell[⚠ At Risk],
  ),
  [], [Achieve \$2M ARR], [\$1.8M],
  [], [Close 50 enterprise deals], [38],
)
