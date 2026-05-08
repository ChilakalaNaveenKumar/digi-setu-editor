// Tutorial 02 — basics: shorthand gates, integer cells, row breaks.
// First circuit: H, four empty cells, then a meter.
// Second circuit: a CNOT (control on top wire, target on bottom).

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, $H$, 4, meter()
)

#v(1em)

#quantum-circuit(
  1, $H$, ctrl(1), 1, [\ ],
  2, targ(), 1
)
