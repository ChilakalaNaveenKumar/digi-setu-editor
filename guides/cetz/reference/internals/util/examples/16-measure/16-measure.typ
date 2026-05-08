#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  get-ctx(ctx => {
    let (w, h) = cetz.util.measure(ctx, [Hello])
    content((0, 0), [measure([Hello]) = (#w, #h)])
  })
})
