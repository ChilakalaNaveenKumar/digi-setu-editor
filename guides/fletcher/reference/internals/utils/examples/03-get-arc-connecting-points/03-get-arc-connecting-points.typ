// Internals/utils 03 — same start/end, three different bend angles
// drawn with cetz.draw.arc + the geometry returned by
// `get-arc-connecting-points`.

#import "@preview/fletcher:0.5.8" as fletcher
#set page(width: auto, height: auto, margin: 6pt)

#fletcher.cetz.canvas({
  let from = (0cm, 0cm)
  let to = (4cm, 0cm)
  fletcher.cetz.draw.circle(from, radius: 2pt, fill: black)
  fletcher.cetz.draw.circle(to,   radius: 2pt, fill: black)
  for (theta, paint) in (
    (15deg,  red),
    (45deg,  blue),
    (90deg,  green.darken(20%)),
  ) {
    let g = fletcher.get-arc-connecting-points(from, to, theta)
    fletcher.cetz.draw.arc(g.center,
      start: g.start, stop: g.stop, radius: g.radius,
      anchor: "origin",
      stroke: 0.7pt + paint,
      mark: (end: ">"))
  }
})
