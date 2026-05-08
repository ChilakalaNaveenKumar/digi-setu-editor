// Internals/marks 03 — draw-mark inside a cetz canvas.

#import "@preview/fletcher:0.5.8" as fletcher
#import fletcher.cetz
#set page(width: auto, height: auto, margin: 6pt)

#context {
  let head = fletcher.resolve-mark(fletcher.MARKS.get().head)
  cetz.canvas({
    fletcher.draw-mark(
      head,
      stroke: 2pt + black,
      origin: (1, 0),
      angle: 0deg,
    )
  })
}
