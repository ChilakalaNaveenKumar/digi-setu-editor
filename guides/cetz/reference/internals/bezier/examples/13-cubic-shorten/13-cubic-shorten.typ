#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `cubic-shorten` is invoked when the engine needs to leave room for a
// mark at the end of a path. The end of the visible curve is
// "shortened" so the arrowhead fits cleanly.
#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (4, 0), (1, 2), (3, -2), mark: (end: ">"))
})
