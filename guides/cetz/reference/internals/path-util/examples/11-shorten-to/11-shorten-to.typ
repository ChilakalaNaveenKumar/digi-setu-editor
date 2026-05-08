#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `shorten-to` is what makes room at the end of an arrowed path. The
// visual effect of this shortening is automatic when you give a shape a
// mark.
#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (3, 0), mark: (end: ">"))
  line((0, -.5), (3, -.5))  // not shortened
})
