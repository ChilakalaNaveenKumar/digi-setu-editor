// Tutorial 01 — Getting Started.
// The minimum viable Touying deck.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

= Title
== First Slide
Hello, Touying!
#pause
Hello, Typst!

== Second Slide
The canvas just works — no `set page(...)` needed.
#pause
Each `#pause` is a new subslide.

= Conclusion
== Wrap up
This is the bare minimum.
For more, see the rest of the tutorial.
