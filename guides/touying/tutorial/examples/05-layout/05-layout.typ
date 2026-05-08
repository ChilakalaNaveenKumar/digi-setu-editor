// Tutorial 05 — Page Layout.
// Custom margins/header/footer + multi-column composer + lazy-v.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-page(
    margin: (x: 4em, y: 2em),
    header: align(top)[#text(gray)[Custom header]],
    footer: align(bottom)[#text(gray)[Custom footer]],
    header-ascent: 0em,
    footer-descent: 0em,
  ),
)

== Two columns via composer
#slide(composer: (1fr, 1fr))[
  *Left column.*
  #lorem(20)
][
  *Right column.*
  #lorem(20)
]

== Asymmetric columns
#slide(composer: (1fr, 2fr))[
  *Narrow.* #lorem(8)
][
  *Wide.* #lorem(20)
]

== `cols` + `lazy-v`
#cols[
  #block(fill: luma(220), inset: .5em, radius: .2em, width: 100%)[
    #lorem(10)
    #lazy-v(1fr)
    Bottom left.
  ]
][
  #block(fill: luma(220), inset: .5em, radius: .2em, width: 100%)[
    #lorem(20)
    #lazy-v(1fr)
    Bottom right.
  ]
]

== `breakable: false` + `clip: true`
#show: touying-set-config.with(config-common(breakable: false, clip: true))
This slide will visually clip overflow.
#lorem(50)
