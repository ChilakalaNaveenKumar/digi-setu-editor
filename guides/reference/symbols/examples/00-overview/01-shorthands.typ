// SHORTHAND sequences are concise multi-character text patterns that the
// PARSER recognizes and translates into specific glyphs.
//
// Two distinct shorthand sets:
//   1. MARKUP-MODE shorthands (run anywhere outside math)
//   2. MATH-MODE   shorthands (run only inside $...$)
//
// You can disable a shorthand by escaping any of its characters with '\'.
// Escaping ONE char in a multi-char shorthand leaves the OTHERS to maybe
// form a different shorthand.

= Markup-mode shorthands

| input  | output | description |
| ------ | ------ | ----------- |
| `--`   | --     | en dash |
| `---`  | ---    | em dash |
| `...`  | ...    | ellipsis |
| `-?`   | (soft hyphen, invisible) | hyphenation hint |
| `-`    | (a regular hyphen)       | unchanged in markup |
| `~`    | nbsp                      | non-breaking space (invisible) |

Examples: page 1--3 of the survey ran from 9~AM to noon, but the appendix
covered pp. 4---17. There are still some unanswered questions...

Escape the first '-' to disable the en-dash:
\-- stays as two regular hyphens.

= Math-mode shorthands (inside $...$)

These convert to math symbols only inside dollar-sign blocks.

$ a -> b $ // arrow.r
$ a |-> b $ // arrow.bar
$ a => b $ // arrow.r.double
$ a ==> b $ // arrow.r.double.long
$ a --> b $ // arrow.r.long
$ a ~~> b $ // arrow.r.squiggly
$ a >-> b $ // arrow.r.tail
$ a ->> b $ // arrow.r.twohead
$ a <- b $ // arrow.l
$ a <==> b $ // arrow.l.r.double.long
$ a <-> b $ // arrow.l.r
$ a <--> b $ // arrow.l.r.long

$ a := b quad a ::= b quad a =: b $
$ a != b quad a >= b quad a <= b $
$ a >> b quad a >>> b quad a << b quad a <<< b $
$ a || b $   // double bar (norm)
$ [| a |] $  // semantic brackets
$ a * b quad a ... b quad a - b $

= Escaping math shorthands

$ a \-> b $ // becomes 'a → b' is suppressed -> renders as 'a -> b'
