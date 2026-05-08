// Tequila 02 — graph-state for edges (1,2), (2,0).

#import "@preview/quill:0.7.2": *
#import "@preview/quill:0.7.2": tequila as tq
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  ..tq.graph-state((1, 2), (2, 0))
)
