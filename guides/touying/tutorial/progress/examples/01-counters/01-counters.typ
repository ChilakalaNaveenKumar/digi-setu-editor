// Progress 01 — Slide counters and progress bar.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-page(
    footer: context [
      Slide #utils.slide-counter.display() / #utils.last-slide-number
      #h(1fr)
      // Progress bar in the footer
      #utils.touying-progress(ratio => box(
        width: ratio * 30%, height: 4pt, fill: blue,
      ))
    ],
  ),
)

= Section
== First Slide
The footer shows the slide number and a progress bar.

== Second Slide
Counter and bar update automatically.

== Third Slide
Last "main" slide.

#show: appendix
= Appendix
== Backup
The counter freezes; total is the previous slide's number.
