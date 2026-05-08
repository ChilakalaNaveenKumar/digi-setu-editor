#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  fill(red.lighten(50%))
  circle((0, 0))
  rect((1, -.5), (3, .5))
  fill(green.lighten(60%))
  circle((4, 0))
})
