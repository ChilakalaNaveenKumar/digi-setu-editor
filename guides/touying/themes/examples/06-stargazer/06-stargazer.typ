// Theme — Stargazer.
#import "@preview/touying:0.7.3": *
#import themes.stargazer: *
#import "@preview/numbly:0.1.0": numbly

#show: stargazer-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Stargazer Demo],
    subtitle: [Customize your slide subtitle],
    author: [Touying Agent],
    date: datetime.today(),
    institution: [touying-typ],
    logo: emoji.school,
  ),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))

#title-slide()
#outline-slide()

= Section A
== Subsection A.1
#tblock(title: [Theorem])[
  A simple theorem.
  $ x_(n+1) = (x_n + a / x_n) / 2 $
]
== Subsection A.2
A slide without a title but with *important* information.

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
