#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
#import circuiteria: util

#table(
  columns: 2,
  [*input*], [*rotate-anchor (90° CW)*],
  [`"north"`], [#util.rotate-anchor("north")],
  [`"east"`],  [#util.rotate-anchor("east")],
  [`"south"`], [#util.rotate-anchor("south")],
  [`"west"`],  [#util.rotate-anchor("west")],
)

== Cycle through all four sides

#{
  let a = "north"
  for _ in range(4) {
    [#a → ]
    a = util.rotate-anchor(a)
  }
  [#a]
}
