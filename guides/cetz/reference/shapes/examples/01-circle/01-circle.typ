#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  // Draw a circle with center (0, 0)
  circle((0, 0))
  // Draw an ellipse
  circle((2, 0), radius: (1, 0.5))

  let (a, b) = ((5, 1), (4, 1))
  // Circle with its center at (5, 1), going through (4, 1)
  circle(a, b)
  set-style(content: (frame: "circle", padding: 1pt, fill: white))
  content(a, [A]); content(b, [B])
})
