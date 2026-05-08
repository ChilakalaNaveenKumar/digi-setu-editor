// Multi-file architecture — shared globals.
// Imported by both main.typ and content.typ.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#let alert-box(body) = block(
  fill: red.lighten(80%),
  inset: .5em,
  radius: .25em,
  width: 100%,
  body,
)
