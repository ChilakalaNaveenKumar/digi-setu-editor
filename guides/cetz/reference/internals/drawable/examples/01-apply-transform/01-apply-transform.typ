#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let d  = cetz.drawable.line-strip(((0, 0, 0), (1, 0, 0)))
  let m  = cetz.matrix.transform-translate(0, 1, 0)
  let d2 = cetz.drawable.apply-transform(m, d)
  content((0, 0), [transformed start = #repr(d2.first().segments.first().slice(1))])
})
