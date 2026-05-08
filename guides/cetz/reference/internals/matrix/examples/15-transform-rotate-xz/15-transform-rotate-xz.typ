#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let m = cetz.matrix.transform-rotate-xz(30deg, 60deg)
  let r = cetz.matrix.round(m, precision: 3)
  content((0, 0), [rot-xz(30°,60°) = #repr(r)])
})
