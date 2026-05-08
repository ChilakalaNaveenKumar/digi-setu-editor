#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== Plain placement

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), [Hello World!])
})

== Text on a line (auto-rotated)

#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (3, 1), name: "line")
  content(
    ("line.start", 50%, "line.end"),
    angle: "line.end",
    padding: .1,
    anchor: "south",
    [Text on a line],
  )
})

== Content in a rectangle between two coordinates

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), (2, 2), box(
    par(justify: false)[This is a long text.],
    stroke: 1pt,
    width: 100%,
    height: 100%,
    inset: 1em,
  ))
})
