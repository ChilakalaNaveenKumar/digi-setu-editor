#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#let im(V) = V.at(1)

#cetz.canvas({
  import cetz.draw: *
  content((0, 0), [im((3, 4)) = #im((3, 4))])
})
