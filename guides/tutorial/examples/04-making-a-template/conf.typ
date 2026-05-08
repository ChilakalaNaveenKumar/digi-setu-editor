#let conf(
  title: [Untitled],
  authors: (),
  abstract: [],
  doc,
) = {
  set page(
    paper: "us-letter",
    header: align(right + horizon, title),
    columns: 2,
    numbering: "1",
  )
  set par(justify: true)
  set text(size: 11pt)

  show heading.where(level: 1): set align(center)
  show heading.where(level: 1): set text(size: 13pt, weight: "regular")
  show heading.where(level: 1): smallcaps

  show heading.where(level: 2): set text(
    size: 11pt, weight: "regular", style: "italic",
  )
  show heading.where(level: 2): it => it.body + [.]

  place(
    top + center, float: true, scope: "parent", clearance: 2em,
    {
      title

      let count = authors.len()
      let ncols = calc.min(count, 3)
      grid(
        columns: (1fr,) * ncols,
        row-gutter: 24pt,
        ..authors.map(a => align(center)[
          #a.name \
          #a.affiliation \
          #link("mailto:" + a.email)
        ]),
      )

      par(justify: false)[
        *Abstract* \
        #abstract
      ]
    },
  )

  doc
}
