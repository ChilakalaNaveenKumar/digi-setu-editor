#set page(width: 16cm, height: auto, margin: 8pt)

== Block image (default), with explicit width and alt text

#image("_assets/star.svg", width: 30%, alt: "Blue star on a yellow square")

== Inline (wrapped in a `box`)

A small icon #box(image("_assets/star.svg", height: 1em,
                        alt: "blue star")) sitting in running text.

== `fit` modes (300pt × 50pt page)

#set page(width: 300pt, height: 60pt, margin: 6pt)
#image("_assets/star.svg", width: 100%, height: 100%, fit: "cover",
       alt: "covered star")

#set page(width: 300pt, height: 60pt, margin: 6pt)
#image("_assets/star.svg", width: 100%, height: 100%, fit: "contain",
       alt: "contained star")

#set page(width: 300pt, height: 60pt, margin: 6pt)
#image("_assets/star.svg", width: 100%, height: 100%, fit: "stretch",
       alt: "stretched star")

#set page(width: 16cm, height: auto, margin: 8pt)

== SVG preprocessed before rendering

#let svg = read("_assets/star.svg")
#let recolored = svg.replace("#2B80FF", green.to-hex())

#image(bytes(recolored), width: 30%,
       alt: "Same star, recolored green")

== Raw pixel data (4×4 grayscale ramp)

#image(
  bytes(range(16).map(x => x * 16)),
  format: (encoding: "luma8", width: 4, height: 4),
  width: 1.5cm,
  scaling: "pixelated",
  alt: "Tiny grayscale ramp",
)
