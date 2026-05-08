#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  group(name: "g", {
    content((1, 0), [Normal])
    content((0, 1), [Normal])
    floating(content((.5, 1.5), [Floating]))
  })
  set-style(stroke: red)
  rect("g.north-west", "g.south-east")
})
