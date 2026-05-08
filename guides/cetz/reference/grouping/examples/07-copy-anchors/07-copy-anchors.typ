#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  group(name: "g", {
    rect((0, 0), (2, 1), name: "r")
    copy-anchors("r")            // expose r's anchors on g directly
  })
  // Now g.north-east comes from r.north-east
  circle("g.north-east", radius: .1, fill: red)
  circle("g.south-west", radius: .1, fill: blue)
})
