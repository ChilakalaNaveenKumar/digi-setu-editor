#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let m = cetz.matrix.transform-rotate-xyz(30deg, 20deg, 10deg)
  let r = cetz.matrix.round(m, precision: 3)
  content((0, 0), [xyz(30°,20°,10°) = #repr(r)])
})
