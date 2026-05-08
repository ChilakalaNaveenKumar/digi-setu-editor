// Demonstrates: string literals (always double-quoted) and the standard
// escapes inside them: \"  \\  \n  \r  \t  \u{HEX}.

#let plain = "release-2026.03"
#let with-quote = "build labelled \"green\""
#let with-newline = "line1\nline2"
#let unicode-in-str = "rocket: \u{1f680}"

Plain: #plain
Quoted: #with-quote
Length of newline-string: #with-newline.len()
Unicode: #unicode-in-str
