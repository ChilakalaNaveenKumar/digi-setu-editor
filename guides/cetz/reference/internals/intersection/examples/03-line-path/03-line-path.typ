#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `intersections()` is the canonical user-facing element that uses
// `line-path` and `path-path` internally.
#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (3, 1.5), name: "l")
  rect((0.5, 0.25), (2.5, 1), name: "r")
  intersections("x", "l", "r")
  for-each-anchor("x", a => {
    circle("x." + a, radius: .07, fill: red)
  })
})
