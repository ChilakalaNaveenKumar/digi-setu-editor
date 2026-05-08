#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== Scoped state

#cetz.canvas({
  import cetz.draw: *
  group({
    stroke(5pt)
    scale(.5); rotate(45deg)
    rect((-1, -1), (1, 1))
  })
  rect((-1, -1), (1, 1))    // outside group: defaults restored
})

== Reaching nested anchors

#cetz.canvas({
  import cetz.draw: *
  group(name: "a", {
    circle((), name: "b")
  })
  circle("a.b.south", radius: 0.2)
  circle((name: "a", anchor: "b.north"), radius: 0.2)
})
