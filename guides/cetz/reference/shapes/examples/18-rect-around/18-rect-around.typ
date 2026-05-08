#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  circle((1, 1), radius: 0.1, fill: blue, name: "c1")
  circle((0, 1), radius: 0.1, fill: red,  name: "c2")
  rect((0, 2), (1, 2.5), name: "r1")
  rect-around("c1", "c2", "r1", stroke: yellow, padding: 0.1)
})
