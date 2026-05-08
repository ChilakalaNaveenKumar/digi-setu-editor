#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let a = (0, 0, 0)
  let b = (2, 1, 0)
  let c = (1, 2, 0)
  let center = cetz.util.calculate-circle-center-3pt(a, b, c)
  for p in (a, b, c) {
    circle(p, radius: .07, fill: red)
  }
  circle(center, radius: .07, fill: blue)
  content((center.at(0), center.at(1) - 0.4), [centre])
})
