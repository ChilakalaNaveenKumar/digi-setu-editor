#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  group(name: "g", {
    circle((0, 0))
    anchor("x", (.4, .1))
    circle("x", radius: .2)
  })
  circle("g.x", radius: .1, fill: red)

  anchor("x", (3, 1))
  circle("x", radius: .15, fill: green)
})
