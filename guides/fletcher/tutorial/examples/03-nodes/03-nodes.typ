// Tutorial 03 — node basics, shapes, groups.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#import fletcher.shapes: pill, parallelogram, diamond, hexagon
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node((0,0), $f$),
  node((1,0), $f$, stroke: 1pt),
  node((2,0), $f$, stroke: blue, shape: rect),
  node((3,0), $f$, stroke: 1pt, radius: 6mm, extrude: (0, 3)),
)

#v(0.6em)

#diagram(
  node-fill: blue.lighten(80%),
  node-stroke: blue,
  node((0,0), [Pill],         shape: pill),
  node((1,0), [Slant],        shape: parallelogram.with(angle: 20deg)),
  node((0,1), [Choice],       shape: diamond),
  node((1,1), [Stop],         shape: hexagon),
)

#v(0.6em)

#diagram(
  node-stroke: 0.6pt,
  node((0,1), [X]),
  node((1,0), [Y], name: <y>),
  node($Sigma$, enclose: ((0,1), <y>),
    stroke: teal, fill: teal.lighten(90%), name: <group>),
  node((2.5, 0.5), [Z], name: <z>),
  edge(<group>, <z>, "->"),
)
