// Theme — Dewdrop.
#import "@preview/touying:0.7.3": *
#import themes.dewdrop: *
#import "@preview/numbly:0.1.0": numbly

#show: dewdrop-theme.with(
  aspect-ratio: "16-9",
  footer: self => self.info.institution,
  navigation: "mini-slides",
  config-info(
    title: [Dewdrop Demo],
    subtitle: [Mini-slides navigation],
    author: [Touying Agent],
    date: datetime.today(),
    institution: [touying-typ],
  ),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))

#title-slide()
#outline-slide()

= Section A
== Subsection A.1
$ x_(n+1) = (x_n + a/x_n) / 2 $

== Subsection A.2
A slide with *important* infos.

= Section B
== Subsection B.1
#lorem(40)

#focus-slide[Wake up!]

== Subsection B.2
We can use `#pause` to #pause display something later.

#show: appendix
= Appendix
== Appendix
Please pay attention to the current slide number.
