#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  // Print the transformation matrix
  get-ctx(ctx => {
    content((), [#repr(ctx.transform)])
  })
})

#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (1, 1), name: "l")
  // Resolve "l.start" / "l.end" to actual vectors and label them
  get-ctx(ctx => {
    let (ctx, a, b) = cetz.coordinate.resolve(ctx, "l.start", "l.end")
    content("l.start", [#a], frame: "rect", stroke: none, fill: white)
    content("l.end",   [#b], frame: "rect", stroke: none, fill: white)
  })
})
