#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  get-ctx(ctx => {
    content((0,  0), [resolve-number(2.5) = #cetz.util.resolve-number(ctx, 2.5)])
    content((0, -.5), [resolve-number(1cm) = #cetz.util.resolve-number(ctx, 1cm)])
  })
})
