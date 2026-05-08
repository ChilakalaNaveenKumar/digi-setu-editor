#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  compound-path({
    rect((-1, -1), (1, 1))
    circle((0, 0), radius: .5)
  }, fill: blue, fill-rule: "even-odd")
})
