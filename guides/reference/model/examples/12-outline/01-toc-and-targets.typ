// 'outline(title: ?, target: heading, depth: none, indent: auto)' generates
// a table of contents (or a list of any other element kind).
//
// Most-used parameters:
//   title    none | auto | content   localized title or override
//                                       auto = "Contents" (en)
//   target   element function or selector that picks elements to list
//                default: heading
//   depth    none | int              max nesting level to include (none = all)
//   indent   auto | relative | function(int) -> length
//                auto: indent inner numbers under the parent's title
//                relative: fixed indent per level
//                function: full control

#set heading(numbering: "1.")

#outline(title: [Table of Contents], depth: 2)
#line(length: 100%)
#outline(
  title: [Figures],
  target: figure.where(kind: image),
)
#line(length: 100%)
#outline(
  title: [Tables],
  target: figure.where(kind: table),
)

= Introduction
#lorem(15)

#figure(
  rect(width: 80pt, height: 30pt, fill: blue.lighten(70%))[image stand-in],
  caption: [Synthetic image figure 1.],
)

== Background
#lorem(20)

= Methods

#figure(
  table(columns: 2, [Yes], [No], [42], [-1]),
  caption: [A small table.],
)

== Setup
#lorem(15)

=== Hardware
#lorem(15)   // not in TOC since depth: 2

= Results

#figure(
  rect(width: 80pt, height: 30pt, fill: green.lighten(70%))[image stand-in],
  caption: [Synthetic image figure 2.],
)
