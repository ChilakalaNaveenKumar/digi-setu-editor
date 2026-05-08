#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// Marks placed at start, end, and midway along a line.
#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (3, 0), mark: (start: "<", end: ">"))
  // A second mark placed mid-path via the `pos` slot:
  line((0, -1), (3, -1), mark: (start: ">", end: ">", pos: 0.5, symbol: ">"))
})
