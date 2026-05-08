#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let d = cetz.drawable.line-strip(
    ((0, 0, 0), (1, 0, 0), (1, 1, 0)),
    close: true,
    stroke: 1pt + blue,
  )
  content((0, 0), [#d.len() drawable(s)])
})
