#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let a = (style: (fill: blue, stroke: 1pt))
  let b = (style: (fill: red))
  let merged = cetz.util.merge-dictionary(a, b)
  content((0, 0), [merged = #repr(merged)])
})
