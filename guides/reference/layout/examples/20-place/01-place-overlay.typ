// 'place(alignment: start, scope: "column", float: false, clearance: 1.5em,
//        dx: 0pt, dy: 0pt, body)' positions content relative to its parent.
//
// 'alignment' controls the anchor:
//   - When 'float: false', any alignment except 'auto'
//   - When 'float: true', must be 'auto', 'top', or 'bottom'
// At the TOP LEVEL of a page, place() positions content directly within
// the page's text area. Use page.background / page.foreground for
// positioning relative to the FULL page (incl. margins).

#set page(height: 200pt)

= Overlay placement

Hello, world!

#rect(
  width: 100%, height: 2cm,
  place(horizon + right, square()),
)

#place(
  top + left,
  dx: -5pt, dy: -5pt,
  square(size: 8pt, fill: red),
)

= dx/dy fine-tune position

Anchor at top + center, then offset right and down:

#place(
  top + center,
  dx: 30pt, dy: 20pt,
  text(fill: blue, weight: "bold")[shifted],
)

= Annotate the next word (zero-width inline)

#let annotate(..args) = {
  box(place(..args))   // wrap so 'place' doesn't break the paragraph
  sym.wj
  h(0pt, weak: true)
}

A placed #annotate(square(size: 6pt), dy: 4pt) square inside text.
