#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  assert-version(version(0, 5, 0), max: version(0, 6, 0), hint: "demo")
  circle((0, 0))
})
