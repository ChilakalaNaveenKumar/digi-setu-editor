#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  stroke(2pt + red)
  circle((0, 0))
  rect((1, -.5), (3, .5))
  stroke((paint: blue, thickness: 1pt, dash: "dashed"))
  line((0, -1), (3, -1))
})
