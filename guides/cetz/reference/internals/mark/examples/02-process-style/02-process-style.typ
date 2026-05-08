#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `mark.process-style` is invoked when a shape's mark argument is being
// finalized. We can demonstrate its effect by changing the global mark
// style root.
#cetz.canvas({
  import cetz.draw: *
  set-style(mark: (length: 0.4, width: 0.3))
  line((0, 0), (2, 0), mark: (end: ">"))
  line((0, -.5), (2, -.5), mark: (end: ">"))
})
