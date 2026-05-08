#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  cetz.decorations.flat-brace((0, 1),  (2, 1))
  cetz.decorations.flat-brace((0, 0),  (2, 0), curves: .2, aspect: 25%)
  cetz.decorations.flat-brace((0, -1), (2, -1), outer-curves: 0, aspect: 75%)
})
