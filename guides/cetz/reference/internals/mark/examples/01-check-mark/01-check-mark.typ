#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `mark.check-mark` is invoked behind the scenes whenever a shape
// receives a `mark:` argument. The most readable demonstration is an
// ordinary line with a mark style — the validation runs implicitly.
#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (2, 0), mark: (end: ">"))
})
