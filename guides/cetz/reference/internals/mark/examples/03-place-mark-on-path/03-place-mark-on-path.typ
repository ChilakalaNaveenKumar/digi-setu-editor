#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `mark.place-mark-on-path` is what the engine uses to build start/end
// marks on a line. Here we demonstrate the effect.
#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (3, 0), mark: (start: "<", end: ">"))
})
