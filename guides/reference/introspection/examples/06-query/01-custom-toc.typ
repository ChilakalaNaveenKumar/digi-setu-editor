#set page(width: 14cm, height: auto, margin: 1cm, numbering: "1")
#set heading(numbering: "1.")

#heading(outlined: false)[Table of Contents]

#context {
  let chapters = query(heading.where(level: 1, outlined: true))
  for c in chapters {
    let loc = c.location()
    let nr  = numbering(
      loc.page-numbering(),
      ..counter(page).at(loc),
    )
    [#c.body #h(1fr) #nr \ ]
  }
}

#pagebreak()

= Introduction
#lorem(20)

#pagebreak()

= Methods
#lorem(20)

== Sub-method
#lorem(10)

#pagebreak()

= Discussion
#lorem(20)
