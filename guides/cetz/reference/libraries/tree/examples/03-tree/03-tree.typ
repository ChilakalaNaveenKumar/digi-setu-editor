#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"
#import "@preview/cetz:0.5.0": tree

#cetz.canvas({
  import cetz.draw: *
  set-style(content: (padding: .1))
  tree.tree(([Root], ([A], [A.A], [A.B]), ([B], [B.A])))
})
