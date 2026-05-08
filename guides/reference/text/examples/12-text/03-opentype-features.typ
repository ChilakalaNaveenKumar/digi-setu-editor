// Group 3: OPENTYPE FEATURES exposed as named text fields
//
//   kerning                     bool    on by default; turn off rarely
//   alternates                  bool    enable 'salt' (stylistic alternates)
//   stylistic-set               none | int | array  enable 'ss01'..'ss20'
//   ligatures                   bool    common ligatures ('liga', 'clig')
//   discretionary-ligatures     bool    rare ligatures ('dlig')
//   historical-ligatures        bool    archaic ligatures ('hlig')
//   number-type                 auto | "lining" | "old-style"   ('lnum' / 'onum')
//   number-width                auto | "proportional" | "tabular"  ('pnum' / 'tnum')
//   slashed-zero                bool    'zero' feature
//   fractions                   bool    'frac' feature (DON'T enable globally)
//   features                    array | dict   raw OpenType feature toggles
//                                                 array of strs sets each to 1
//                                                 dict maps feature -> int

= Kerning vs no-kerning

#set text(size: 22pt)
Totally (kerning on)

#set text(kerning: false)
Totally (kerning off, look at the gap between T and o)
#set text(kerning: true)
#set text(size: 11pt)

= Stylistic sets / alternates (font-dependent)

#set text(font: "Libertinus Serif")
Default 'a' g \
#text(alternates: true)[Alternates: a g]

= Lining vs old-style numbers

The year 1234 in lining: #text(number-type: "lining")[1234567890] \
The year 1234 in old-style: #text(number-type: "old-style")[1234567890]

= Tabular vs proportional widths (use tabular in tables)

Proportional: #text(number-width: "proportional")[12 34 56 78] \
Tabular:      #text(number-width: "tabular")[12 34 56 78]

= Slashed zero

Default 0 vs slashed: #text(slashed-zero: true)[0]

= Fractions (use locally only)

#text(fractions: true)[1/2 + 3/4 = 5/4]
(don't set this globally -- it'd hit URLs and casual numbers too)

= Raw features array / dict

// Enable 'frac' explicitly via array.
#set text(features: ("frac",))
1/3

#set text(features: (:))

// Disable a feature (e.g. contextual alternates 'calt') via dict.
#set text(features: (calt: 0))
fi fl ligature attempt
#set text(features: (:))
