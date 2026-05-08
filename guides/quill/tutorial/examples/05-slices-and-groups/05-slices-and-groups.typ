// Tutorial 05 — slices and gate groups.
// Three rows of a syndrome-measurement circuit with a gategroup
// labelled "Syndrome" at the bottom and two vertical slices.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, gate($H$), ctrl(1),
  slice(label: "1"), 1,
  gategroup(3, 3, label: (content: "Syndrome", pos: bottom)),
  1, ctrl(2), ctrl(), 1,
  slice(label: "3", n: 2, stroke: blue),
  2, [\ ],
  2, targ(), 1, ctrl(1), 1, ctrl(), 3, [\ ],
  4, targ(), targ(), meter(target: -2)
)
