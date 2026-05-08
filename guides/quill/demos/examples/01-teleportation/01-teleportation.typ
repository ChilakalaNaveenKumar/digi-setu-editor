// Demo 01 — Quantum teleportation (Nielsen & Chuang, Fig. 4.15).

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  lstick($|psi〉$),       ctrl(1), gate($H$), 1,    ctrl(2), meter(), [\ ],
  lstick($|beta_00〉$, n: 2), targ(),  1,         ctrl(1), 1,    meter(), [\ ],
  3, gate($X$), gate($Z$), midstick($|psi〉$), setwire(0)
)
