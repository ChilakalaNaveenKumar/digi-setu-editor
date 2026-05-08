// Gallery 19 — controlled-Z: dot+dot.
#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, ctrl(1), 1, [\ ],
  1, ctrl(),  1,
)
