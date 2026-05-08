#set page(width: 12cm, height: auto, margin: 1cm, numbering: "1")

== Where am I right now?

#context [
  Page (physical): #here().page() \
  Position dictionary: #repr(here().position())
]

== Anchored queries with `here()`

= Section A
= Section B
= Section C

#context [
  Headings before this point: #query(
    selector(heading).before(here())
  ).len()
]
