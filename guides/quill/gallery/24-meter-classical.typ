// Gallery 24 — meter to classical wire.
#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, meter(target: 1), 1, [\ ],
  setwire(2), 1, ctrl(), 1,
)
