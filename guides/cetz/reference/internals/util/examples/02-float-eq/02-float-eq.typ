#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  content((0,  0), [float-eq(0.1 + 0.2, 0.3) = #cetz.util.float-eq(0.1 + 0.2, 0.3)])
  content((0, -.5), [float-eq(1, 2) = #cetz.util.float-eq(1, 2)])
})
