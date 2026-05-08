#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  set-style(polygon: (radius: 0.65))
  polygon((0, 0), 3, angle: 90deg)
  polygon((1.5, 0), 5)
  polygon((3, 0), 7)
})
