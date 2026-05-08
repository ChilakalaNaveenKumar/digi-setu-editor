#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let a = cetz.matrix.transform-translate(1, 0, 0)
  let b = cetz.matrix.transform-rotate-z(90deg)
  let c = cetz.matrix.mul-mat(a, b)
  let r = cetz.matrix.round(c, precision: 3)
  content((0, 0), [translate · rotate-z(90°) = #repr(r)])
})
