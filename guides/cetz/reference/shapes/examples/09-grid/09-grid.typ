#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  // Draw a grid
  grid((0, 0), (2, 2))
  // Draw a smaller blue grid
  grid((1, 1), (2, 2), stroke: blue, step: .25)
})
