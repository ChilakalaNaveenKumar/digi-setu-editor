#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let (a, b, c) = ((0, 0), (1, 1), (2, -1))
  bezier-through(a, b, c, name: "curve")
  set-style(content: (frame: "circle", padding: 1pt, fill: white))
  content(a, [A]); content(b, [B]); content(c, [C])
  content("curve.ctrl-1", [2]); content("curve.ctrl-0", [1])
})
