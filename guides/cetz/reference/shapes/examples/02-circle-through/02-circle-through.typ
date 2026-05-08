#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let (a, b, c) = ((0, 0), (2, -0.5), (1, 1))
  circle-through(a, b, c, name: "c")
  set-style(content: (frame: "circle", padding: 1pt, fill: white))
  content(a, [A]); content(b, [B]); content(c, [C])
})
