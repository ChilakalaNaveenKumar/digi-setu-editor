#set page(width: 16cm, height: auto, margin: 8pt)

== Linear, radial, conic side-by-side

#stack(
  dir: ltr, spacing: 8pt,
  square(size: 50pt, fill: gradient.linear(..color.map.rainbow)),
  square(size: 50pt, fill: gradient.radial(..color.map.rainbow)),
  square(size: 50pt, fill: gradient.conic(..color.map.rainbow)),
)

== Custom stops with explicit positions
// Either every stop has an offset or none of them does.

#rect(
  width: 100%, height: 18pt,
  fill: gradient.linear((red, 0%), (yellow, 30%), (green, 60%), (blue, 100%)),
)

== Direction (angle) for linear gradients

#stack(
  dir: ltr, spacing: 6pt,
  square(size: 40pt, fill: gradient.linear(red, blue, angle: 0deg)),
  square(size: 40pt, fill: gradient.linear(red, blue, angle: 90deg)),
  square(size: 40pt, fill: gradient.linear(red, blue, angle: 180deg)),
  square(size: 40pt, fill: gradient.linear(red, blue, angle: 270deg)),
)

== Sharp (palette-style) and repeated

#let grad = gradient.linear(..color.map.viridis)
#rect(width: 100%, height: 14pt, fill: grad)
#v(2pt)
#rect(width: 100%, height: 14pt, fill: grad.sharp(5))
#v(2pt)
#rect(width: 100%, height: 14pt, fill: grad.sharp(5, smoothness: 30%))
#v(2pt)
#rect(width: 100%, height: 14pt,
      fill: gradient.linear(red, blue).repeat(4, mirror: true))

== Gradient on text (relative: parent)

#set text(20pt, weight: "bold",
          fill: gradient.linear(red, blue, relative: "parent"))
Painted across one shared gradient.
#set text(fill: black, weight: "regular", size: 10pt)

== Sampling

`viridis` at 0%, 25%, 50%, 75%, 100%:
#let g = gradient.linear(..color.map.viridis)
#for t in (0%, 25%, 50%, 75%, 100%) [
  #box(width: 16pt, height: 16pt, fill: g.sample(t), stroke: 0.5pt + black)
  #h(2pt)
]
