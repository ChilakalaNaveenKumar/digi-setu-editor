#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let merged = cetz.styles.merge(
    (fill: blue,  stroke: 1pt),
    (fill: red,   radius: 0.5),
  )
  content((0, 0), [merged = #repr(merged)])
})
