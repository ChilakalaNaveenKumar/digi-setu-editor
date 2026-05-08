#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// process.many() is implicitly invoked by cetz.canvas when it walks the
// body you supply. The example shows two elements being processed in
// order.
#cetz.canvas({
  import cetz.draw: *
  circle((0, 0), radius: .3, fill: blue)
  circle((1, 0), radius: .3, fill: red)
})
