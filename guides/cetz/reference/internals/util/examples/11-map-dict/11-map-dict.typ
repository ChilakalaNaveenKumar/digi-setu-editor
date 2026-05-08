#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let d = (a: 1, b: 2, c: 3)
  let mapped = cetz.util.map-dict(d, (k, v) => v * 10)
  content((0, 0), [map-dict = #repr(mapped)])
})
