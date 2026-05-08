#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let p = cetz.intersection.line-line((0, 0), (3, 3), (0, 3), (3, 0))
  line((0, 0), (3, 3))
  line((0, 3), (3, 0))
  if p != none {
    circle(p, radius: .08, fill: red)
  }
})
