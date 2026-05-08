#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let s = cetz.vector.add((1, 2, 3), (10, 20, 30))
  content((0, 0), [add = #repr(s)])
})
