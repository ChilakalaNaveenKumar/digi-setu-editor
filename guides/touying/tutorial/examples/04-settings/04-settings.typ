// Tutorial 04 — Settings and Config.
// config-info, preamble, touying-set-config, slide(config:).
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Settings Demo],
    author: [Touying agent],
    date: datetime.today(),
  ),
)

== Normal Slide
This slide uses the default settings.

== Blue Background Slide
#show: touying-set-config.with(config-page(fill: blue.lighten(80%)))
This slide and all following ones have a blue background.

== Red Accent Slide
#show: touying-set-config.with(config-colors(primary: red))
#alert[This is an alert box with red accent color.]

== Local Override
#slide(config: config-page(fill: purple.lighten(90%)))[
  Only this slide has a light purple background.
]

== Closing Slide
This is the final slide of the settings demo.
