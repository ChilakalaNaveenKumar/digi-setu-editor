#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  circle((), name: "c")
  get-ctx(ctx => {
    let (_, p) = cetz.coordinate.resolve(ctx, "c.east")
    content((0, 0), [c.east = #repr(p)])
  })
})
