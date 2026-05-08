#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (2, 1), stroke: gray)
  cetz.decorations.zigzag(
    line((0, 0), (2, 1)),
    amplitude: .25,
    start: 10%,
    stop:  90%,
  )
})
