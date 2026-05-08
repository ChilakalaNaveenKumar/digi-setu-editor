// 'symbol' is a Unicode glyph value. Built-in symbols come from two modules:
//
//   sym.*    general symbols (arrows, math, punctuation, currencies, ...)
//            -- in MATH MODE you can drop the 'sym.' prefix.
//   emoji.*  every standard emoji.
//
// Symbols can have MODIFIERS, accessed by chained dot syntax. Order doesn't
// matter; Typst picks the variant that has all attached modifiers and the
// fewest extra ones.

right arrow:        #sym.arrow.r
not greater-equal:  #sym.gt.eq.not

math-mode shorthand (no 'sym.' prefix):
$ a gt.eq.not b $

emoji:              #emoji.face.halo

// Modifier order is irrelevant -- both pick the same variant.
order A: #sym.arrow.r.long
order B: #sym.arrow.long.r
