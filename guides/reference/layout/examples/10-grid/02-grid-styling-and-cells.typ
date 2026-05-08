// Per-cell overrides via 'grid.cell':
//   colspan / rowspan
//   x / y                  pin to specific position (auto-flow skips)
//   fill / align / inset / stroke / breakable
//
// Manual lines: 'grid.hline' / 'grid.vline' (override per-cell strokes).
//
// 'grid.header' / 'grid.footer' mark header and footer rows that REPEAT
// when the grid breaks across pages.

#set page(width: 360pt, height: auto)

= Per-cell styling

#grid(
  columns: 5,
  align: center,
  inset: (x: 2pt, y: 3pt),
  fill: (rgb("#239dad50"), none),
  stroke: (x, y) => if calc.rem(x + y, 3) == 0 { 0.5pt },
  ..range(5 * 3).map(n => numbering("A", n + 1)),
)

= Header/footer + manual hline/vline

#import grid: cell, header, footer

#set grid(stroke: 0.5pt + gray)
#show grid.cell.where(y: 0): strong

#grid(
  columns: 3,
  header(
    [Substance], [Sub-critical °C], [Super-critical °C],
  ),
  [HCl],     [12.0], [92.1],
  [NaMS],    [16.6], [104],
  [KOH],     cell(colspan: 2)[24.7],
  footer(
    cell(colspan: 3, align: right)[_Source: lab notebook._],
  ),
)
