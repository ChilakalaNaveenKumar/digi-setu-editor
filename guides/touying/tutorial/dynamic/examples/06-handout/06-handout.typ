// Dynamic 06 — Handout mode collapses subslides.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-common(handout: true),
)

= Title
== Animated Slide
First item.
#pause
Second item (won't generate a separate page in handout mode).
#pause
Third item.

== Handout-only Slide <touying:handout>
This slide only appears when `handout: true`.

== Normal Slide
Always visible — second / third item collapse into the same page.
