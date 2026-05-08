// Reference 05 — phantom() variants.
// Phantom sized by content, then phantom sized by width/height.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(1, phantom(content: $H$), 1, $H$, 1)

#v(0.6em)

#quantum-circuit(1, phantom(width: 1cm), 1, $X$, 1)
