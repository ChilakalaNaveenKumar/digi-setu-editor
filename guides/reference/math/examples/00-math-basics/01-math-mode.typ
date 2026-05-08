// MATH MODE basics. Enter math mode by wrapping content in '$ ... $'.
//
// INLINE vs BLOCK:
//   $x^2$            -> inline (no surrounding spaces inside the $$)
//   $ x^2 $          -> BLOCK (whitespace right after opening $ AND right
//                       before closing $ promotes the equation to its own
//                       centered block)
//
// VARIABLES vs WORDS:
//   single letters    -> rendered as VARIABLES (italic by default)
//   multi-letter      -> rendered as IDENTIFIERS / function names (upright)
//   To force a word as plain text in math, QUOTE it: "area"
//   To inject a code value, use HASH:                #x

= Inline vs block

This is inline: $x^2 + y^2 = z^2$. Variables in inline math sit on the
text baseline.

A block equation gets its own centered line:
$ x^2 + y^2 = z^2 $

= Variables, words, and code injection

$ A = pi r^2 $
$ "area" = pi dot "radius"^2 $
$ cal(A) := { x in RR | x "is natural" } $

#let x = 5
$ #x < 17 $
