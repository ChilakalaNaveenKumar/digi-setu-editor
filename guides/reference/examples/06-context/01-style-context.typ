#set page(width: 14cm, height: auto, margin: 1cm)

== Style context: the same `value` reads its surrounding lang

#let value = context text.lang

current: #value \

#[
  #set text(lang: "de")
  german scope: #value \
]

#[
  #set text(lang: "fr")
  french scope: #value \
]
