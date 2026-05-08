#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let p = cetz.util.ellipse-point((0, 0, 0), (2, 1), 45deg)
  circle((0, 0), radius: (2, 1))
  circle(p, radius: .07, fill: red)
})
