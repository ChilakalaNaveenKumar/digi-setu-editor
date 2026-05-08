#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  hobby((0, 0), (1, 1.2), (2, -.8), (3, 0))
  hobby((0, -2), (1, -1), (2, -3), (3, -2), close: true)
})
