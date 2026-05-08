#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  circle((), radius: .25)         // first circle uses default previous (0,0)
  move-to((1, 0))
  circle((), radius: .15)         // second circle uses (1,0) as previous
})
