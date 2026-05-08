#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let d = cetz.vector.dot((1, 2, 3), (4, 5, 6))
  content((0, 0), [dot = #d])
})
