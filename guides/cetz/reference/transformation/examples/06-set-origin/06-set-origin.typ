#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  // Draw some rect
  rect((0, 0), (2, 2), name: "r")
  // Move (0, 0) to the top edge of "r"
  set-origin("r.north")
  circle((0, 0), radius: .1, fill: white)
})
