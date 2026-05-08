// Theme — Aqua.
#import "@preview/touying:0.7.3": *
#import themes.aqua: *

#show: aqua-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Aqua Demo],
    subtitle: [Beautiful blue gradient],
    author: [Touying Agent],
    date: datetime.today(),
    institution: [touying-typ],
  ),
)

#title-slide()
#outline-slide()

= The Section
== Slide Title
#lorem(40)

#focus-slide[
  Another variant with primary color in background...
]

== Summary
#slide(self => [
  #align(center + horizon)[
    #set text(size: 3em, weight: "bold", fill: self.colors.primary)
    THANKS FOR ALL
  ]
])
