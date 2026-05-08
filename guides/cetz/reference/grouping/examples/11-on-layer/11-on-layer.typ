#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  set-style(stroke: none)
  content((0, 0), [This is an example.], name: "text")
  on-layer(-1, {
    circle("text.north-east", radius: .3, fill: red)
    circle("text.south",      radius: .4, fill: green)
    circle("text.north-west", radius: .2, fill: blue)
  })
})
