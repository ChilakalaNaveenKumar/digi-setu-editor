#set page(width: 14cm, height: auto, margin: 1cm)

== Accumulating computation

#let star = state("star", 0)
#let compute(expr) = {
  star.update(prev => eval(expr.replace("⭐", str(prev))))
  [New value: #context star.get(). \ ]
}

#compute("10")
#compute("⭐ + 3")
#compute("⭐ * 2")
#compute("⭐ - 5")

== Current-chapter running header

#let chapter = state("chapter", "")
#show heading.where(level: 1): h => {
  chapter.update(h.body)
  h
}

#set page(header: context align(right, emph(chapter.get())))

#pagebreak()
= Introduction
Some intro text.

#pagebreak()
= Methods
Some methods text.

== Time travel
Final star value at end of document: #context star.final()
