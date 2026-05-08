#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let m = cetz.matrix.transform-translate(2, 3, 0)
  let p = cetz.matrix.mul4x4-vec3(m, (1, 1, 0))
  content((0, 0), [translate · (1,1,0) = #repr(p)])
})
