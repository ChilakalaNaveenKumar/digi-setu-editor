#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let d = cetz.matrix.dim(cetz.matrix.ident(4))
  content((0, 0), [dim(ident(4)) = #repr(d)])
})
