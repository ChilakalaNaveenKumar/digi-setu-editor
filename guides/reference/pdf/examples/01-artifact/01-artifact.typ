#set page(
  width: 14cm,
  height: auto,
  margin: 1.5cm,
  background: pdf.artifact[
    #place(center + horizon,
      rotate(-30deg, text(60pt, gray.lighten(70%))[DRAFT]))
  ],
)

= A page with a "DRAFT" watermark

The watermark is a PDF artifact, so screen readers and PDF text
extraction will skip over it entirely.

#lorem(80)

#pdf.artifact[
  #align(center, text(20pt, gray)[\* \* \*])
]

#lorem(60)
