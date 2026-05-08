// Custom theme — quick override of metropolis primary color + footer.
#import "@preview/touying:0.7.3": *
#import themes.metropolis: *

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  config-colors(primary: rgb("#1a6b8a")),
  footer: self => self.info.author,
  config-info(
    title: [Custom Metropolis],
    author: [Touying Agent],
    date: datetime.today(),
  ),
)

#title-slide()

= Section
== Slide
Content with the custom teal-blue primary color.

#focus-slide[
  Same theme, very different look.
]
