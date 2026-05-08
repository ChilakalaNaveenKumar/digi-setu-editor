#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `cubic-shorten-linear` and `cubic-shorten` underlie how marks make
// room at the end of a curve. We can demonstrate the *visible effect*
// by adding marks to a bezier shape:
#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (4, 0), (1, 2), (3, -2), mark: (start: ">", end: ">"))
})
