// 'class(class, body)' forces a math class on content. The class controls
// SPACING and ATTACHMENT POSITIONING.
//
// Available classes:
//   "normal"       default
//   "punctuation"  comma-like spacing
//   "opening"      ( -like
//   "closing"      ) -like
//   "fence"        | -like (same on both sides)
//   "large"        sum-like (gets limits in block)
//   "relation"     = -like (extra space around it)
//   "unary"        not-like
//   "binary"       times-like
//   "vary"         + -like (unary or binary depending on context)

= Heart symbol re-classified as a relation

#let loves = math.class("relation", sym.suit.heart)

$ x loves y and y loves 5 $
// Without the relation class, 'sym.suit.heart' would render with normal
// (tight) spacing. Reclassifying it spaces it like '=' or '<'.

= Custom 'large' operator gets limits in block mode

#let myop = math.class("large", math.upright[Op])
$ myop_(i = 1)^n a_i $

= Treat a symbol as an opening delimiter

#let bigslash = math.class("opening", $\\$)
$ bigslash a, b ] $
