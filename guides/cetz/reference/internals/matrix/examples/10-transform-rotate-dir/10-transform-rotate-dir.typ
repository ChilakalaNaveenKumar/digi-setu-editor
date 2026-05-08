#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let m = cetz.matrix.transform-rotate-dir((1, 0, 0), (0, 1, 0))
  content((0, 0), [rotate-dir(x, y) = #repr(m)])
})
