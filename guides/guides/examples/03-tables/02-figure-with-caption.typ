#set page(width: 14cm, height: auto, margin: 1cm)

#figure(
  table(
    columns: 2,
    align: (left, right),
    stroke: (top: 0.7pt, bottom: 0.7pt, x: none),
    table.header[Item][Price],
    [Bread], [\$3.50],
    [Milk],  [\$2.75],
    [Apples], [\$4.10],
  ),
  caption: [Grocery prices in USD.],
) <prices>

See @prices for details.

== Compact key/value (borderless)

#table(
  columns: 2, stroke: none, inset: (x: 6pt, y: 3pt),
  align: (right, left),
  [*Title*], [A Fluid Dynamic Model],
  [*Authors*], [Tungsten, Deklan],
  [*Year*], [2026],
)
