// External — PDFPC metadata + speaker notes.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#pdfpc.config(
  duration-minutes: 30,
  start-time: datetime(hour: 14, minute: 10, second: 0),
  end-time:   datetime(hour: 14, minute: 40, second: 0),
  last-minutes: 5,
  note-font-size: 12,
)

#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-info(title: [PDFPC Demo]),
)

== First Slide
Visible content here.

#pdfpc.speaker-note("Reminder: pause for 30s before clicking.")

#speaker-note[
  Touying-style note (content form):
  - Time check: 5 min mark.
  - Don't forget to mention the demo URL.
]

== Second Slide
The pdfpc metadata is queried via:
```
typst query --root . ./04-pdfpc.typ --field value --one "<pdfpc-file>" > 04-pdfpc.pdfpc
```
