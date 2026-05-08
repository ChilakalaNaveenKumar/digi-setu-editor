#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import circuiteria: util

#table(
  columns: 2,
  [*input*], [*opposite-anchor*],
  [`"north"`], [#util.opposite-anchor("north")],
  [`"east"`],  [#util.opposite-anchor("east")],
  [`"south"`], [#util.opposite-anchor("south")],
  [`"west"`],  [#util.opposite-anchor("west")],
)
