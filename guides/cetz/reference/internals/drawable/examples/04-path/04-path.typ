#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  // A path is built from an array of subpaths.
  // Each subpath is `(origin, closed, segments)`.
  // Each segment is `("l", point)` for a line or `("c", c1, c2, end)` for a cubic.
  let p = cetz.drawable.path(
    stroke: 1pt + black,
    (
      ((0, 0, 0), false, (
        ("l", (1, 0, 0)),
        ("l", (1, 1, 0)),
      )),
    ),
  )
  content((0, 0), [type = #repr(p.type)])
})
