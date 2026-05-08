#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

== Default canvas (auto-sized)

#cetz.canvas({
  import cetz.draw: *
  circle((0, 0))
  rect((1, 0), (3, 1))
})

== Custom unit length

#cetz.canvas(length: 0.5cm, {
  import cetz.draw: *
  circle((0, 0))
  rect((1, 0), (3, 1))
})

== Debug bounding boxes

#cetz.canvas(debug: true, {
  import cetz.draw: *
  circle((0, 0))
  rect((1, 0), (3, 1))
})

== Background + padding

#cetz.canvas(background: aqua.lighten(70%), padding: .5, {
  import cetz.draw: *
  circle((0, 0))
})

== Inline canvas (set baseline)

A wee circle: #cetz.canvas(baseline: (0, 0), length: 0.5em, {
  import cetz.draw: *
  circle((0, 0), radius: 0.6, fill: blue)
}) finishes the sentence.
