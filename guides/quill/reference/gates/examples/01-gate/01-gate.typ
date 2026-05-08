// Reference 01 — gate() variants.
// Square, round, D-shaped, coloured.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, gate($H$), 1, [\ ],
  1, gate($X$, radius: 100%), 1, [\ ],
  1, gate($Y$, radius: (right: 100%)), 1, [\ ],
  1, gate($Z$, fill: red.lighten(60%)), 1
)
