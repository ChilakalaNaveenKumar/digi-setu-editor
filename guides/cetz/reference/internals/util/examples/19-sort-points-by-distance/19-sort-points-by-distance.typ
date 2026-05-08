#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let base = (0, 0, 0)
  let pts  = ((3, 4, 0), (1, 1, 0), (2, 0, 0))
  let sorted = cetz.util.sort-points-by-distance(base, pts)
  content((0, 0), [sorted = #repr(sorted)])
})
