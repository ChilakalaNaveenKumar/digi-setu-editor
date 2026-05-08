// Demo 06 — Fault-tolerant π/8 gate (Nielsen & Chuang, Ex. 10.66).

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#let group = gategroup.with(stroke: (dash: "dotted", thickness: .5pt))

#quantum-circuit(
  group(1, 4, padding: (left: 1.5em)), lstick($|0〉$), nwire(""), $H$, $T$,
    ctrl(1), $S X$, rstick($T|psi〉$), [\ ],
  lstick($|psi〉$), nwire(""), 2, targ(), meter(target: -1),
)
