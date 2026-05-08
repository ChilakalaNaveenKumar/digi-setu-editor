// Tutorial 07 — manual x:/y: placement.
// Graph state via spread map + gategroup pinned with x:/y:.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  ..range(4).map(i => lstick($|0〉$, y: i, x: 0)),
  ..range(4).map(i => gate($H$, y: i, x: 1)),
  2,
  ctrl(2), 1, ctrl(1), 1, [\ ],
  3, ctrl(2), ctrl(), [\ ],
  2, ctrl(), [\ ],
  3, ctrl()
)

#v(0.8em)

#quantum-circuit(
  1, $S^dagger$, $H$, ctrl(), $H$, $S$, 1, [\ ],
  3, ctrl(-1),
  gategroup(2, 5, x: 1, y: 0, stroke: purple,
    label: (pos: bottom, content: text(purple)[CY gate])),
  gategroup(2, 3, x: 2, y: 0, stroke: blue,
    label: text(blue)[CX gate]),
)
