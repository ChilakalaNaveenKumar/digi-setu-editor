// 'lorem(words: int) -> content' generates Latin-like blind text. Useful
// for layout testing without writing real content.
//
// The output sequence is RANDOMLY chosen, but DETERMINISTIC for the same
// 'words' value -- 'lorem(30)' always produces the same 30 words.

= 5 words
#lorem(5)

= 30 words
#lorem(30)

= Repeat with same arg = identical output
#lorem(8) \
#lorem(8)

= Used for layout placeholders inside other elements

#figure(
  rect(width: 60%, height: 30pt, fill: blue.lighten(80%))[image stand-in],
  caption: lorem(8),
)

#enum(
  lorem(6),
  lorem(10),
  lorem(4),
)
