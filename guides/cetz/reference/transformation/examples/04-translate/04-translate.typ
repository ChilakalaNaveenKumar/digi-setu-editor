#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  // Outer rect
  rect((0, 0), (2, 2))
  // Inner rect after translate
  translate(x: .5, y: .5)
  rect((0, 0), (1, 1))
})
