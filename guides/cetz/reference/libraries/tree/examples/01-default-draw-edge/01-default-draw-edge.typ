#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  cetz.tree.tree(
    ([Root], ([A], [A.A], [A.B]), ([B], [B.A])),
    draw-edge: (p, c) => {
      set-style(stroke: 1pt + gray)
      cetz.tree.default-draw-edge(p, c)
    },
  )
})
