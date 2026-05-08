// 'fill' and 'align' (and 'inset' and 'stroke') accept a FUNCTION
// '(x, y) -> value' where x is the column index and y is the row index
// (both 0-based). This is how you build striped tables and conditional
// styling.

#table(
  columns: 4,
  fill: (x, _) => if calc.odd(x) { luma(240) } else { white },
  align: (x, y) => {
    if y == 0 { center }
    else if x == 0 { left }
    else { right }
  },
  table.header(
    [], [*Q1*], [*Q2*], [*Q3*],
  ),
  [Revenue:], [1000 €], [2000 €], [3000 €],
  [Expenses:], [500 €], [1000 €], [1500 €],
  [Profit:], [500 €], [1000 €], [1500 €],
)

= Per-column inset

#table(
  columns: 3,
  inset: (left: 12pt, right: 12pt, y: 6pt),
  table.header([Name], [Score], [Notes]),
  [Alice], [97], [perfect attendance],
  [Bob],   [82], [skipped lab 3],
  [Carol], [88], [excellent lab work],
)
