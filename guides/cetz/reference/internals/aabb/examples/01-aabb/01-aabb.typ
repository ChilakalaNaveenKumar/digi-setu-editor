#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `aabb` is internal. The visible analog is the canvas's `debug` flag,
// which exposes per-element bounding boxes computed via these helpers.
#cetz.canvas(debug: true, {
  import cetz.draw: *
  circle((0, 0))
  rect((1.5, -.5), (3, 1))
})
