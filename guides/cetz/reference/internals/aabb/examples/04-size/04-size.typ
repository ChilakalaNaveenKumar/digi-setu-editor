#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `aabb.size` is internal. The user-visible analog is the canvas auto-
// sizing — its width and height come from the bounding box of all
// drawables.
#cetz.canvas(debug: true, {
  import cetz.draw: *
  rect((0, 0), (3, 1.5))
})
