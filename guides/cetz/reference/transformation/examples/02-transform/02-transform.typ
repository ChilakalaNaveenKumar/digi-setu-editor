#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  rect((0, 0), (1, 1))
  // Stack a 30deg z-rotation on top of the current transform
  transform(cetz.matrix.transform-rotate-z(30deg))
  rect((1.5, 0), (2.5, 1))
})
