#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  rect((0, 0), (2, 2))
  set-viewport((0, 0), (2, 2), bounds: (10, 10))
  circle((5, 5))
})
