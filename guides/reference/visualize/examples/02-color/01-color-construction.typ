#set page(width: 16cm, height: auto, margin: 8pt)
#let chip(c) = box(width: 22pt, height: 22pt, fill: c, stroke: 0.5pt + black)

== Constructing colors

#chip(rgb("#239dad"))
#chip(rgb(255, 100, 0))
#chip(rgb(40%, 60%, 80%))
#chip(luma(120))
#chip(oklab(60%, 0.1, -0.1))
#chip(oklch(70%, 0.15, 200deg))
#chip(color.hsl(30deg, 80%, 50%))
#chip(cmyk(20%, 80%, 0%, 10%))

== Predefined named colors

#for name in (
  ("black", black), ("gray", gray), ("silver", silver),
  ("navy", navy), ("blue", blue), ("aqua", aqua),
  ("red", red), ("orange", orange), ("yellow", yellow),
  ("green", green), ("lime", lime), ("purple", purple),
) [
  #chip(name.at(1)) #raw(name.at(0)) #h(6pt)
]

== Color maps via `color.map`

#stack(
  dir: ttb, spacing: 4pt,
  rect(width: 100%, height: 12pt, fill: gradient.linear(..color.map.viridis)),
  rect(width: 100%, height: 12pt, fill: gradient.linear(..color.map.crest)),
  rect(width: 100%, height: 12pt, fill: gradient.linear(..color.map.inferno)),
)

== Manipulating an existing color

#let base = rgb("#3b82f6")
#chip(base)            // base
#chip(base.lighten(40%))
#chip(base.darken(30%))
#chip(base.saturate(20%))
#chip(base.desaturate(60%))
#chip(base.rotate(120deg))
#chip(base.negate())
#chip(base.transparentize(50%))

== Mixing

#chip(red.mix(blue))                                   // perceptual midpoint
#chip(red.mix(blue, space: rgb))                       // RGB midpoint
#chip(color.mix(red, green, blue))                     // three-way average
#chip(color.mix((red, 70%), (blue, 30%)))              // weighted

== Inspection

Hex of `red.lighten(20%)`: #raw(red.lighten(20%).to-hex()) \
Components of `oklch(70%, 0.15, 200deg)`:
#raw(repr(oklch(70%, 0.15, 200deg).components()))
