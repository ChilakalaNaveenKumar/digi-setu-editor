// Tutorial 07 — CeTZ integration: hand-drawn Bézier edge.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node((0, 1), $A$, stroke: 1pt, shape: fletcher.shapes.diamond),
  node((2, 0), [Bezier], fill: purple.lighten(80%)),
  render: (grid, nodes, edges, options) => {
    fletcher.cetz.canvas({
      fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
      let n1 = fletcher.find-node-at(nodes, (0, 1))
      let n2 = fletcher.find-node-at(nodes, (2, 0))
      let out-angle = 45deg
      let in-angle = -110deg
      fletcher.get-node-anchor(n1, out-angle, p1 => {
        fletcher.get-node-anchor(n2, in-angle, p2 => {
          let c1 = (to: p1, rel: (out-angle, 10mm))
          let c2 = (to: p2, rel: (in-angle, 20mm))
          fletcher.cetz.draw.bezier(p1, p2, c1, c2,
            mark: (end: ">"))
        })
      })
    })
  },
)
