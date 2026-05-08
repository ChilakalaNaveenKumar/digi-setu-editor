#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let d = cetz.vector.sub((10, 20, 30), (1, 2, 3))
  content((0, 0), [sub = #repr(d)])
})
