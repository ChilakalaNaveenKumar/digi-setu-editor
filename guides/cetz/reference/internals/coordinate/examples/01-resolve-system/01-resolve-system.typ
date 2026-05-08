#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  get-ctx(ctx => {
    let kinds = (
      cetz.coordinate.resolve-system(ctx, (1, 2, 3)),
      cetz.coordinate.resolve-system(ctx, (45deg, 1)),
      cetz.coordinate.resolve-system(ctx, "circ"),
      cetz.coordinate.resolve-system(ctx, (rel: (1, 0))),
    )
    content((0, 0), [systems = #repr(kinds)])
  })
})
