#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  bezier-through((0, 0), (1, 2), (3, 0))
  for p in ((0, 0), (1, 2), (3, 0)) {
    circle(p, radius: .06, fill: red)
  }
})
