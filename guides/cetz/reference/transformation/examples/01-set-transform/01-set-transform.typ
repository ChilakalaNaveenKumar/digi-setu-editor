#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  rect((0, 0), (1, 1))
  set-transform(cetz.matrix.transform-translate(2, 0, 0))
  rect((0, 0), (1, 1))
  set-transform(none)            // reset to identity
  rect((0, 1.5), (1, 2.5))
})
