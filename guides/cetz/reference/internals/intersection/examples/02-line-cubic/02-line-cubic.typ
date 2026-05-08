#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let pts = cetz.intersection.line-cubic(
    (0, 0.5), (4, 0.5),
    (0, 0), (4, 0), (1, 2), (3, -2),
  )
  bezier((0, 0), (4, 0), (1, 2), (3, -2))
  line((0, 0.5), (4, 0.5))
  for p in pts {
    circle(p, radius: .07, fill: red)
  }
})
