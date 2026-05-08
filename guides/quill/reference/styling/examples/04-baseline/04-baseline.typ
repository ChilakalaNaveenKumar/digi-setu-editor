// Styling 04 — baseline alignment.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

// Inline circuit with a small negative baseline so it sits just below
// the surrounding text baseline.
Hello #quantum-circuit(baseline: -2pt, 1, $H$, 1) world.

#v(0.6em)

// Larger negative offset.
Eq: #quantum-circuit(baseline: -8pt, 1, $H$, ctrl(1), [\ ], 1, targ()) end.
