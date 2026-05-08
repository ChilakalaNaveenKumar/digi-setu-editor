#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let row = cetz.vector.as-mat((1, 2, 3))
  let col = cetz.vector.as-mat((1, 2, 3), mode: "column")
  content((0,  0), [row = #repr(row)])
  content((0, -.6), [col = #repr(col)])
})
