#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  scope({
    stroke(2pt + red)
    fill(yellow.lighten(50%))
    rect((0, 0), (2, 1), name: "r")
  })
  // The named element "r" leaked out of scope and is reachable here:
  circle("r.north-east", radius: .15, fill: blue)
})
