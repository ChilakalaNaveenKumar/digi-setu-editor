#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (4, 0), (1, 2), (3, -2), name: "c")
  line((0, 0.5), (4, 0.5), name: "l")
  intersections("x", "c", "l")
  for-each-anchor("x", a => {
    circle("x." + a, radius: .07, fill: red)
  })
})
