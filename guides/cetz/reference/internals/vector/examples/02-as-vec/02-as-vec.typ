#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let a = cetz.vector.as-vec((1, 2))
  let b = cetz.vector.as-vec((1,), init: (9, 9, 9))
  content((0,  0), [as-vec((1, 2)) = #repr(a)])
  content((0, -.6), [as-vec((1,), init: (9, 9, 9)) = #repr(b)])
})
