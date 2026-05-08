// Gallery 12 — multi-qubit gate spanning 3 wires.
#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(wires: 3, 1, mqgate($U$, n: 3), 1)
