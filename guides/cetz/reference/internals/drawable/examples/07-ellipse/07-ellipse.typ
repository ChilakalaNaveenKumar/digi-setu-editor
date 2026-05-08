#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let d = cetz.drawable.ellipse(0, 0, 0, 1, 0.5, stroke: 1pt + black)
  content((0, 1.5), [#d.len() drawable(s)])
  // The ellipse drawable is rendered indirectly by the circle shape:
  circle((0, 0), radius: (1, 0.5))
})
