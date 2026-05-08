#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  set-style(content: (padding: .1))
  cetz.tree.tree(
    ([Root], ([A], [A.A], [A.B]), ([B], [B.A])),
    draw-node: node => {
      rect((-.4, -.3), (.4, .3), fill: aqua.lighten(70%))
      cetz.tree.default-draw-node(node)
    },
  )
})
