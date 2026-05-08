#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  content((0,  0), [circle-arclen(1) = #cetz.util.circle-arclen(1)])
  content((0, -.5), [circle-arclen(1, angle: 90deg) = #cetz.util.circle-arclen(1, angle: 90deg)])
})
