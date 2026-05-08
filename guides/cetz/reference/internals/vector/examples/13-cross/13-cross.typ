#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let c = cetz.vector.cross((1, 0, 0), (0, 1, 0))
  content((0, 0), [cross = #repr(c)])
})
