// Gallery 21 — full swap (× + ×).
#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, swap(1), 1, [\ ],
  1, swap(),  1,
)
