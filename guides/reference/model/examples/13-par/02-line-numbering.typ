// 'par.line' configures paragraph LINE NUMBERING. Set rules must occur
// BEFORE any page content (numbering scope must be uniform across each
// page run -- a page run = sequence of pages without an explicit pagebreak).
//
// Key fields:
//   numbering         none|str|function(int)->content     numbering pattern
//   number-align      auto | alignment                    L/R alignment of numbers
//   number-margin     alignment ('start' | 'end' | 'left' | 'right')
//   number-clearance  auto | length                       gap between number and text
//   numbering-scope   "document" | "page"                 reset behaviour

#set par.line(
  numbering: n => text(fill: red)[#n],
  number-margin: start,
  numbering-scope: "page",
)

// Disable numbers inside figures (typical pattern).
#show figure: set par.line(numbering: none)

Roses are red. \
Violets are blue. \
Typst is there for you.

#figure(
  caption: [No line numbers in this figure.],
)[
  Lorem ipsum \
  dolor sit amet
]

After the figure, the line counter continues:

#lorem(40)
