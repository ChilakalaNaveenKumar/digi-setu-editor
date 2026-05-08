#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  rect((0, 0),  (rel: (1, 1)), radius: 0)
  rect((2, 0),  (rel: (1, 1)), radius: 25%)
  rect((4, 0),  (rel: (1, 1)), radius: (north: 50%))
  rect((6, 0),  (rel: (1, 1)), radius: (north-east: 50%))
  rect((8, 0),  (rel: (1, 1)), radius: (south-west: 0, rest: 50%))
  rect((10, 0), (rel: (1, 1)), radius: (rest: (20%, 50%)))
})
