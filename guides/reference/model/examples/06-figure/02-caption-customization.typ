// 'figure.caption' is the caption sub-element. You configure it with
// set / show rules independently of the figure itself.
//
//   position    top | bottom            (default bottom)
//   separator   auto | content          between number and body
//   body        the caption's content   (used in show rules)
//
// Available fields on the caption element inside show rules:
//   it.kind        the figure's kind
//   it.supplement  the localized word ("Figure", "Table", "Atom", ...)
//   it.counter     the underlying counter (use with .display to show numbering)
//   it.numbering   the numbering pattern
//   it.body        the caption text

#set figure.caption(separator: [ -- ])

#figure(
  rect(width: 70pt, height: 30pt, fill: blue.lighten(70%))[A],
  caption: [Default position (bottom), custom separator.],
)

#show figure.where(kind: table): set figure.caption(position: top)

#figure(
  table(columns: 2, [Yes], [No], [42], [-1]),
  caption: [Tables get their captions on top via show-set.],
)

#show figure.caption: it => [
  #underline(it.body) | #it.supplement #context it.counter.display(it.numbering)
]

#figure(
  rect(width: 70pt, height: 30pt, fill: green.lighten(70%))[B],
  caption: [Fully custom caption: underlined body + manually placed counter.],
)
