#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  set-style(fill: aqua, stroke: 1pt + black)
  set-style(circle: (radius: .35))
  set-style(rect: (radius: 25%))
  set-style(line: (mark: (end: ">", scale: 1.2)))

  circle((0, 0))
  rect((1, -.5), (3, .5))
  line((0, -1), (3, -1))
})
