#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (4, 0), (1, 2), (3, -2), name: "b")
  bezier((0, 1), (4, 1), (3, -2), (1, 4), name: "c")
  intersections("x", "b", "c")
  for-each-anchor("x", a => {
    circle("x." + a, radius: .07, fill: red)
  })
})
