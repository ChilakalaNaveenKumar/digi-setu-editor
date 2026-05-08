#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (4, 0), (1, 2), (3, -2), name: "c")
  circle("c.30%", radius: .07, fill: red)
  circle("c.70%", radius: .07, fill: blue)
})
