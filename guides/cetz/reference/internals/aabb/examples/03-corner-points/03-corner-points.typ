#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `corner-points` is internal. The named border anchors on a `rect`
// expose the same four corners on the front face.
#cetz.canvas({
  import cetz.draw: *
  rect((0, 0), (3, 1.5), name: "r")
  for c in ("south-west", "south-east", "north-east", "north-west") {
    circle("r." + c, radius: .07, fill: red)
  }
})
