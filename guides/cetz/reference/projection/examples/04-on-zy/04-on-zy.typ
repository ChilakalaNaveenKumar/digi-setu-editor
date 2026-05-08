#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  ortho({
    on-zy({
      rect((-1, -1), (1, 1))
    })
  })
})
