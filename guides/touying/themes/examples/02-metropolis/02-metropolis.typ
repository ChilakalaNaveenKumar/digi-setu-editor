// Theme — Metropolis.
#import "@preview/touying:0.7.3": *
#import themes.metropolis: *
#import "@preview/numbly:0.1.0": numbly

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  footer: self => self.info.institution,
  config-info(
    title: [Metropolis Demo],
    subtitle: [A Touying theme],
    author: [Touying Agent],
    date: datetime.today(),
    institution: [touying-typ],
    contact: [contact\@mail.com],
    logo: emoji.city,
  ),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))

#title-slide()

= Outline <touying:hidden>
#outline(title: none, indent: 1em, depth: 1)

= First Section
---
A slide without a title but with some *important* information.

== A title
$ x_(n+1) = (x_n + a/x_n) / 2 $

= Second Section
#focus-slide[Wake up!]

== Simple Animation
We can use `#pause` to #pause display something later.

#show: appendix
= Appendix
---
Please pay attention to the current slide number.
