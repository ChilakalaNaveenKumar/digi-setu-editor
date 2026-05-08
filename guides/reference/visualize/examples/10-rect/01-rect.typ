#set page(width: 16cm, height: auto, margin: 8pt)

== Empty default and content-sized

#rect()
#h(8pt)
#rect[Auto sized to fit the content.]

== Explicit width / height

#rect(width: 60%, height: 24pt, fill: aqua)

== Per-side stroke dictionary

#rect(
  width: 100%, height: 30pt,
  stroke: (top: 2pt + red, bottom: 2pt + red, rest: 0.5pt + black),
  inset: 6pt,
)[Top and bottom are red.]

== Rounded corners (uniform and per-corner)

#rect(width: 6cm, radius: 6pt, inset: 8pt,
      fill: yellow.lighten(60%))[Uniform rounding]

#v(4pt)

#rect(
  width: 6cm, inset: 8pt,
  radius: (top-left: 12pt, top-right: 0pt,
           bottom-right: 12pt, bottom-left: 0pt),
  fill: green.lighten(70%),
)[Slanted-tag look]

== Card with `inset` and `outset`

#block(
  fill: gray.lighten(85%), inset: 16pt,
  rect(
    width: 100%, inset: 12pt, fill: white,
    radius: 6pt, stroke: 0.5pt + black,
    outset: (left: 6pt, right: 6pt, rest: 0pt),
  )[Card uses `outset` to bleed slightly into its parent's padding.],
)

== Top-only border (callout)

#rect(
  width: 100%, inset: 8pt,
  stroke: (top: 2pt + maroon, rest: none),
)[Note: top-only border for emphasis.]
