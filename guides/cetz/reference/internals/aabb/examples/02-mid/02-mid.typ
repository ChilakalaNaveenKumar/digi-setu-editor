#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `aabb.mid` is internal. The user-visible equivalent is the bounding
// box's `center` border anchor on a shape.
#cetz.canvas({
  import cetz.draw: *
  rect((0, 0), (3, 1.5), name: "r")
  circle("r.center", radius: .07, fill: red)
})
