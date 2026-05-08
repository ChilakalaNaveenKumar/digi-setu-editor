#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== Quadratic

#cetz.canvas({
  import cetz.draw: *
  let (a, b, c) = ((0, 0), (2, 0), (1, 1))
  bezier(a, b, c)
  set-style(content: (frame: "circle", padding: 1pt, fill: white))
  content(a, [A]); content(b, [B]); content(c, [C])
})

== Cubic

#cetz.canvas({
  import cetz.draw: *
  let (a, b, c, d) = ((0, 0), (2, 0), (.5, -1), (1.5, 1))
  bezier(a, b, c, d)
  set-style(content: (frame: "circle", padding: 1pt, fill: white))
  content(a, [A]); content(b, [B]); content(c, [C]); content(d, [D])
})
