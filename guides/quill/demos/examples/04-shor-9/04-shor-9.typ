// Demo 04 — Shor 9-qubit code encoder (Nielsen & Chuang, Fig. 10.4).

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#let ancillas = (
  setwire(0), 5, lstick($|0〉$), setwire(1), targ(), 2, [\ ],
  setwire(0), 5, lstick($|0〉$), setwire(1), 1, targ(), 1,
)

#quantum-circuit(
  scale: 80%,
  lstick($|psi〉$), 1, 10pt, ctrl(3), ctrl(6), $H$, 1, 15pt,
    ctrl(1), ctrl(2), 1, [\ ],
  ..ancillas, [\ ],
  lstick($|0〉$), 1, targ(), 1, $H$, 1, ctrl(1), ctrl(2),
    1, [\ ],
  ..ancillas, [\ ],
  lstick($|0〉$), 2, targ(), $H$, 1, ctrl(1), ctrl(2),
    1, [\ ],
  ..ancillas
)
