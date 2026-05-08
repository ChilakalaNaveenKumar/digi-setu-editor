// 'terms' (DEFINITION / GLOSSARY LIST):
//
// MARKUP SHORTHAND:
//   / Term: Description
// (forward slash, term, colon, description). Description may span multiple
// lines via indentation, just like list/enum bodies.
//
// Most-used fields:
//   separator       content     between term and description (default: thin space)
//   indent          length      whole-item indent
//   hanging-indent  length      indent for description continuation lines
//   spacing         auto|length item-to-item spacing
//   tight           markup-driven (blank lines = wide)
//
// 'terms.item(term, description)' lets you build entries programmatically.

= Default separator (a small weak space)

/ Ligature: A merged glyph.
/ Kerning: A spacing adjustment between two adjacent letters.
/ Hinting: Per-pixel rendering hints for low-resolution displays. The
  description can span multiple lines and the hanging indent keeps it
  visually grouped under the term.

= Custom separator

#set terms(separator: [ -- ])

/ EM dash: Three hyphens become one em dash.
/ EN dash: Two hyphens become one en dash.

= Hanging-indent off

#set terms(hanging-indent: 0pt, separator: [ : ])

/ Plain: Continuation lines start at the left margin instead of being
  indented under the term.

= Programmatic and for-loop forms

#terms(
  terms.item([TeX], [Born in 1978.]),
  terms.item([LaTeX], [Born in 1984.]),
  terms.item([Typst], [Born in 2019.]),
)

#for (year, product) in (
  "1978": "TeX",
  "1984": "LaTeX",
  "2019": "Typst",
) [/ #product: Born in #year.]
