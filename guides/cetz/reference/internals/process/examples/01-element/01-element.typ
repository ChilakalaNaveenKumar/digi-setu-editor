#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// process.element() is normally invoked by cetz.canvas itself; calling it
// from user code is rarely useful. We demonstrate that the type exists
// and that the cetz pipeline runs end-to-end.
#cetz.canvas({
  import cetz.draw: *
  circle((0, 0), radius: .4, fill: blue)
  content((1.2, 0), [process.element runs me])
})
