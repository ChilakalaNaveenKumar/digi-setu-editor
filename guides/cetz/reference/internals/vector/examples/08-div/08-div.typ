#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let s = cetz.vector.div((2, 4, 6), 2)
  content((0, 0), [div = #repr(s)])
})
