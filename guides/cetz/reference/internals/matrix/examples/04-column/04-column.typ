#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let m = cetz.matrix.ident(4)
  let c = cetz.matrix.column(m, 2)
  content((0, 0), [column(ident(4), 2) = #repr(c)])
})
