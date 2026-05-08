// Tutorial 02 — Code Styles.
// Simple-style headings + block-style #slide[] in the same deck.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

= Simple Style
== Heading-driven
Hello, Touying!
#pause
Hello, Typst!

---

The `---` token is parsed as `#pagebreak()`.
The previous title is reused.

= Block Style
== Inside `#slide[..]`
#slide[
  Block-style content.
  #pause
  More content.
]

#focus-slide[
  *Focus slide* — primary-color background, large text.
]

= Empty Slide
#empty-slide[
  An empty slide has no header / footer.
]
