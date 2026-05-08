#set page(width: 14cm, height: auto, margin: 1cm)
#set heading(numbering: "1.")

= Introduction <intro>
Some text in the introduction.

= Background  <back>
Some text in the background.

== Counter time-travel via labels

#context [
  Current counter: #counter(heading).get() \
  At `here()`:     #counter(heading).at(here()) \
  At `<intro>`:    #counter(heading).at(<intro>) \
  At `<back>`:     #counter(heading).at(<back>)
]

== Nested contexts pick up newer set rules

#set text(lang: "de")
#context [
  #set text(lang: "fr")
  outer: #text.lang \
  inner: #context text.lang
]
