// Progress 02 — Section utilities and progressive outline.
#import "@preview/touying:0.7.3": *
#import themes.dewdrop: *

#show: dewdrop-theme.with(
  aspect-ratio: "16-9",
  config-info(title: [Progressive Outline Demo]),
)

#title-slide()

= Introduction
== Overview <touying:hidden>
#components.progressive-outline()

== Hello
A first slide in section 1.

= Background
== Outline <touying:hidden>
#components.progressive-outline()

== Some background
Now in section 2 — the outline highlights this section.

= Conclusion
== Outline <touying:hidden>
#components.progressive-outline()

== Wrap up
Final section.
