#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let m = cetz.vector.lerp((0, 0, 0), (10, 20, 30), 0.25)
  content((0, 0), [lerp(.., t: 0.25) = #repr(m)])
})
