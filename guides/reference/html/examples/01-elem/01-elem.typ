// Compile with HTML export to see the effect:
//   typst compile --features html --format html 01-elem.typ 01-elem.html
//
// In PDF/SVG/PNG output the html.elem calls produce no visible change
// beyond their inline body; the tags only matter in HTML output.

#let card(body) = context if target() == "html" {
  html.elem("section", attrs: (class: "card"), body)
} else {
  block(stroke: 0.5pt + black, inset: 10pt, radius: 4pt, body)
}

#card[
  = First card
  This card has the same source for HTML and PDF.
]

#card[
  = Second card
  In HTML it is `<section class="card">…</section>`; in PDF it is a
  bordered block.
]

== A `<nav>` that only appears in HTML

#context if target() == "html" {
  html.elem("nav", attrs: ("aria-label": "Site navigation"), [
    - #link("/")[Home]
    - #link("/blog/")[Blog]
  ])
}
