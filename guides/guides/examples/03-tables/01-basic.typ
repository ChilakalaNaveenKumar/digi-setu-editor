#set page(width: 14cm, height: auto, margin: 1cm)

== Basic table with header and footer

#table(
  columns: 3,
  align: (left, right, right),
  table.header[Name][Q1][Q2],
  [Alice], [12], [15],
  [Bob],   [9],  [14],
  [Carol], [17], [11],
  table.footer[Total][38][40],
)

== Spans (colspan + rowspan)

#table(
  columns: 4,
  table.cell(colspan: 4, fill: aqua)[Quarterly report],
  table.cell(rowspan: 2, fill: aqua.lighten(50%))[Q1],
  [Jan], [Feb], [Mar],
  [10],  [20],  [30],
)

== Striped rows via fill function

#table(
  columns: 3,
  align: (left, right, right),
  stroke: (top: 0.7pt, bottom: 0.7pt, x: none),
  fill: (_, row) => if calc.odd(row) and row > 0 { silver.lighten(70%) },
  table.header[Name][Q1][Q2],
  [Alice], [12], [15],
  [Bob],   [9],  [14],
  [Carol], [17], [11],
  [Dave],  [3],  [8],
)
