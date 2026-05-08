#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  catmull((0, 0), (1, 1), (2, -1), (3, 0), tension: .4, stroke: blue)
  catmull((0, 0), (1, 1), (2, -1), (3, 0), tension: .5, stroke: red)
})
