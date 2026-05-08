// Dynamic 01 — Simple animations: pause and meanwhile.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

== Pause
#slide[
  First #pause Second
  #pause
  Third
]

== Meanwhile
#slide[
  First
  #pause
  Second
  #meanwhile
  Third
  #pause
  Fourth
]
