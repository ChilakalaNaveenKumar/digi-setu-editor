// Most-used 'text' parameters group 1: FONT IDENTITY
//
//   font     str | array<str | dict>     family OR priority list of families
//                                           dict form: (name: "...", covers: ...)
//                                           covers: "latin-in-cjk" | regex(...)
//   fallback bool                        last-resort fallback to any font with the glyph
//   style    "normal" | "italic" | "oblique"
//   weight   100..900 | "thin"/"extralight"/"light"/"regular"/"medium"/"semibold"
//                       /"bold"/"extrabold"/"black"
//   stretch  ratio 50%..200%             for fonts with condensed/expanded variants
//   size     length                      basis of the 'em' unit (default 11pt)
//   fill     color | gradient | tiling   glyph paint
//   stroke   stroke value | none         outline (default none)
//   tracking length                      added space between characters
//   spacing  relative                    word-space scale (default 100%)

= Font selection (priority list with fallback)

#set text(font: ("Libertinus Serif", "DejaVu Sans Mono"))
This text prefers Libertinus Serif and falls back to DejaVu Sans Mono for any
glyph it doesn't have. Both are bundled with Typst.

= Style and weight

#text(style: "italic")[Italic] /
#text(style: "oblique")[Oblique] /
#text(weight: "regular")[Regular] /
#text(weight: 500)[Medium (500)] /
#text(weight: "bold")[Bold] /
#text(weight: "black")[Black]

= Size (and 'em' relativity)

#set text(size: 14pt)
14pt base #text(1.5em)[1.5em (= 21pt)] back to 14pt.
#text(0.7em)[0.7em (= 9.8pt)] back to 14pt.

#set text(size: 11pt)

= Fill, stroke, tracking

#text(fill: red)[Red] /
#text(fill: blue, stroke: 0.3pt + black)[Blue glyphs with thin black outline] /
#text(tracking: 1.5pt)[L o o s e l y   t r a c k e d]

= Per-codepoint font with 'covers'

// Use PT Sans for digits only, Libertinus Serif for everything else.
#set text(font: (
  (name: "DejaVu Sans Mono", covers: regex("[0-9]")),
  "Libertinus Serif",
))

The number 12345 is monospace; the rest of this sentence is serif.
