// Internals/node 03 — DFA where each state has a self-loop drawn by
// hand using the resolved `pos.xyz` of the corresponding node. The
// state coords come straight from `resolve-node-coordinates`.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (20mm, 14mm),
  node-stroke: 0.6pt,
  node((0, 0), $q_0$, shape: fletcher.shapes.circle, name: <q0>),
  node((1, 0), $q_1$, shape: fletcher.shapes.circle, name: <q1>),
  node((2, 0), $q_2$, shape: fletcher.shapes.circle,
    extrude: (0, 3), name: <q2>),
  edge((-0.5, 0), <q0>, "->"),
  edge(<q0>, <q1>, "->", $a$),
  edge(<q1>, <q2>, "->", $b$),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    for n in nodes {
      if n.label == none { continue }
      let xyz = n.pos.xyz
      let cx = xyz.at(0)
      let cy = xyz.at(1)
      let r = 5mm
      fletcher.cetz.draw.arc(
        (cx + 1.5mm, cy - 4mm),
        start: -45deg, stop: 225deg,
        radius: r * 0.45,
        mark: (end: ">"),
        stroke: 0.5pt + black,
      )
    }
  })
)
