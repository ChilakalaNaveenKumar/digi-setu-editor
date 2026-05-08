#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `anchor.border` is internal. From the user side, you reach the same
// resolver indirectly by referencing a shape's named border anchor.
#cetz.canvas({
  import cetz.draw: *
  rect((0, 0), (2, 1), name: "r")
  circle("r.east",       radius: .07, fill: red)
  circle("r.north-east", radius: .07, fill: blue)
})
