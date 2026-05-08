// Internals/draw 06 — radial spokes on three different node shapes.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (28mm, 0mm),
  node((0, 0), $bullet$, shape: fletcher.shapes.circle,
    width: 20mm, height: 20mm, stroke: 0.5pt),
  node((1, 0), $bullet$, shape: fletcher.shapes.diamond,
    width: 22mm, height: 18mm, stroke: 0.5pt),
  node((2, 0), $bullet$, shape: fletcher.shapes.hexagon,
    width: 22mm, height: 20mm, stroke: 0.5pt),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    for n in nodes {
      for theta in (0deg, 45deg, 90deg, 135deg, 180deg, 225deg, 270deg, 315deg) {
        fletcher.get-node-anchor(n, theta, p => {
          let centre = (n.pos.xyz.at(0), n.pos.xyz.at(1))
          fletcher.cetz.draw.line(centre, p,
            stroke: 0.4pt + red.transparentize(40%))
        })
      }
    }
  })
)
