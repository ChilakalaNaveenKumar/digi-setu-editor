#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  grid((-1, -1), (1, 1), stroke: gray)
  // Mark with its tip at (0,0) pointing to (1,0)
  mark((0, 0), (1, 0), symbol: ")>", scale: 4)
})

#cetz.canvas({
  import cetz.draw: *
  grid((-1, -1), (1, 1), stroke: gray)
  // Mark with its center at (0,0) pointing to (1,1)
  mark((0, 0), (1, 1), symbol: ">>", anchor: "center", scale: 5)
})
