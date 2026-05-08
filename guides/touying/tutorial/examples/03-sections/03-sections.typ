// Tutorial 03 — Sections, numbering, outline, special labels, appendix.
#import "@preview/touying:0.7.3": *
#import themes.simple: *
#import "@preview/numbly:0.1.0": numbly

#set heading(numbering: numbly("{1}.", default: "1.1"))
#show: simple-theme.with(aspect-ratio: "16-9")

== Outline <touying:hidden>
#components.adaptive-columns(outline(title: none, indent: 1em))

= First Section
== Slide One
Content for slide one.

== Slide Two <touying:unnumbered>
This slide is not counted.

== Hidden Slide <touying:hidden>
You will not see this slide in the output.

= Second Section
== Slide Three
More content.

#show: appendix

= Appendix
== Backup Slide
The slide counter is frozen at the last main slide.
