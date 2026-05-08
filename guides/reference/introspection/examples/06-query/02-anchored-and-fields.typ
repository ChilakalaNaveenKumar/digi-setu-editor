#set page(width: 14cm, height: auto, margin: 1cm)
#set heading(numbering: "1.")

= Section A
= Section B

#context [
  Headings before this point: #query(
    selector(heading).before(here())
  ).len() \
  Total headings:             #query(heading).len()
]

= Section C
= Section D

== List of all heading bodies and levels

#context {
  for h in query(heading) [
    - level #h.level: #h.body \
  ]
}
