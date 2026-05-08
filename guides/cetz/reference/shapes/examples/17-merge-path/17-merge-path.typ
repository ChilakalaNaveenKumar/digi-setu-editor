#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  merge-path(fill: white, {
    line((0, 0), (1, 0))
    bezier((), (0, 0), (1, 1), (0, 1))
  })
})
