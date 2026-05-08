// Demonstrates: leading (line spacing) set as an em-relative length.
// '1em' equals the current font size; '0.65em' is tighter than default.
// em units automatically scale when text size changes.

#set text(size: 11pt)
#set par(justify: true, leading: 0.65em)

This paragraph has tighter line spacing because leading is
set to 0.65em. With size=11pt, that is 7.15pt between
baselines. Use em (not pt) for leading so the spacing
follows the font size if you change it later.
