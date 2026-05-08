// 'float: true' makes the placed element FLOAT to the top or bottom of
// the parent, displacing in-flow content.
//
// 'scope: "parent"' (only with float: true) places relative to the parent
// container -- typically used to span across columns inside a multi-column page.
//
// 'place.flush()' forces all pending floating elements to be placed
// before continuing -- useful to prevent floats from spilling into the
// next section.

#set page(height: 200pt)

= Floating notes alternating top/bottom

#let note(where, body) = place(
  center + where,
  float: true,
  clearance: 6pt,
  rect(body),
)

#lorem(8)
#note(bottom)[Bottom 1]
#note(bottom)[Bottom 2]
#lorem(30)
#note(top)[Top]
#lorem(8)

#pagebreak()

= Span across all columns with scope: "parent"

#set page(columns: 2)

#place(
  top + center,
  scope: "parent",
  float: true,
  rect(width: 80%, fill: aqua, [Title spans both columns]),
)

#lorem(20)

= place.flush() flushes pending floats

#lorem(10)

#figure(
  rect(width: 100%, height: 30pt, fill: orange.lighten(70%)),
  placement: auto,
  caption: [A floating figure],
)

#place.flush()
This text comes AFTER the float (no spillover).
