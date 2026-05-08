// Tutorial 09 — fine-tuning with length items.
// Horizontal 10pt gutter, then vertical 10pt gutter between wires.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  $X$, $Y$, 10pt, $Z$
)

#v(0.6em)

#quantum-circuit(
  $X$, [\ ], $Y$, [\ ], 10pt, $Z$
)
