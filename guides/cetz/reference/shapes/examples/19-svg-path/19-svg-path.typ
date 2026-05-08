#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  svg-path(
    ("h", 2),
    ("anchor", "here"),
    ("c", (0, 1), (0, 0), (-1, 0)),
    ("v", -0.5),
    ("h", -1),
    ("z",),
    name: "svg",
  )
  circle("svg.here", fill: white, radius: 0.1cm)
})
