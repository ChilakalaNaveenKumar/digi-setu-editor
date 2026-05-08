#set page(width: 14cm, height: auto, margin: 8pt)
#set figure(numbering: "1")
#import "@preview/codly:1.3.0": *
#show: codly-init

== reference-by: "line" (default)

#codly(
  highlights: ((line: 2, start: 2, end: 7, label: <hl-1>),),
)

#figure(caption: [Example])[
```typ
= Example
* Hello, world! *
```
] <ex-1>

Reference a highlight by its label: @hl-1.

== reference-by: "item"

#codly(
  reference-by: "item",
  highlights: ((line: 2, start: 2, end: 7, label: <hl-2>, tag: [Highlight]),),
)

#figure(caption: [Example 2])[
```typ
= Example
* Hello, world! Highlight *
```
] <ex-2>

Reference by item: @hl-2.
