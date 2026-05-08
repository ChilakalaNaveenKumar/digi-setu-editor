#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  set-style(circle: (fill: blue, stroke: red))
  get-ctx(ctx => {
    let s = cetz.styles.resolve(ctx.style, root: "circle")
    content((0, 0), [resolved.fill = #repr(s.fill)])
    content((0, -.5), [resolved.stroke = #repr(s.stroke)])
  })
})
