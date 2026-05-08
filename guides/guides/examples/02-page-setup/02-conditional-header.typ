#set page(
  paper: "iso-b6",
  margin: 1.4cm,
  numbering: "1",
  header: context {
    if counter(page).get().first() > 1 [
      _Lisa Strassner's Thesis_  #h(1fr)  Academy
    ]
  },
)

= Title page

#v(1fr)
#align(center)[
  *A Big Important Title* \
  Lisa Strassner — 2026
]
#v(1fr)

#pagebreak()

= First chapter

#lorem(120)

#pagebreak()

= Second chapter

#lorem(120)
