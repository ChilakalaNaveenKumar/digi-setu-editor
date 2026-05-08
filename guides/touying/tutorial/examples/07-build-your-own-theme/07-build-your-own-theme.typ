// Bamboo theme demo — main driver.
// Imports bamboo.typ from the same folder.
#import "@preview/touying:0.7.3": *
#import "bamboo.typ": *

#show: bamboo-theme.with(
  aspect-ratio: "16-9",
  footer: self => self.info.institution,
  config-info(
    title: [Bamboo Theme Demo],
    author: [Touying Agent],
    date: datetime.today(),
    institution: [touying-typ.github.io],
  ),
)

#title-slide()

= First Section
== First Slide
A slide with a title and an *important* information.

== Second Slide
The bamboo color is `#5E8B65` — a nice forest green.

#focus-slide[
  Focus on it!
]

= Conclusion
== Wrap up
Custom theme, ready to ship.
