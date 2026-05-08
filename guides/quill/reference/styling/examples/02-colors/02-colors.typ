// Styling 02 — colors / dark mode + accent theme.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#box(fill: black, quantum-circuit(
  wire: .7pt + white,
  color: white,
  fill: black,
  1, $X$, ctrl(1), rstick([*?*]), [\ ],
  1, 1, targ(), meter(),
))

#v(0.6em)

#quantum-circuit(
  color: blue.darken(20%),
  wire: .8pt + blue.darken(20%),
  fill: blue.lighten(85%),
  1, $H$, ctrl(1), 1, [\ ],
  1, 1, targ(), 1,
)
