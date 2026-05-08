// 'smallcaps(body, all: false)' renders text in small capitals using the
// font's OpenType 'smcp' (and optionally 'c2sc') features.
//
// Fields:
//   all   bool    if true, also turns ALREADY-UPPERCASE letters into small caps
//                   (enables 'c2sc' OpenType feature)
//
// Font support: NOT every font has small caps. If your font lacks them,
// nothing visibly changes. Workarounds:
//   - swap to a font that ships small caps (e.g. Latin Modern Roman Caps)
//   - eventually Typst will synthesize small caps; not yet.
//
//   #show smallcaps: set text(font: "Latin Modern Roman Caps")

= Default (only lowercase letters get small-cap'd)

Hello \
#smallcaps[Hello]

= With 'all: true' (uppercase letters ALSO become smaller small-caps)

#smallcaps[UNICEF] is an agency of #smallcaps[UN].

vs.

#smallcaps(all: true)[UNICEF] is an agency of #smallcaps(all: true)[UN].

= Common heading style: small caps + center + non-bold

#set heading(numbering: "I.")
#show heading: smallcaps
#show heading: set align(center)
#show heading: set text(weight: "regular")

= Introduction

#lorem(20)
