#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `padded` is the same operation that drives the `padding:` option on
// `cetz.canvas`. We can demonstrate visually:
#cetz.canvas(padding: 0.6, {
  import cetz.draw: *
  rect((0, 0), (2, 1), fill: blue.lighten(70%))
})
