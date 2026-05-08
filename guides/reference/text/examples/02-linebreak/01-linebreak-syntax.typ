// 'linebreak(justify: false)' advances to the next line.
//
// MARKUP SHORTHAND: backslash followed by whitespace ('\ ' or '\\n').
// The shorthand always produces an UNJUSTIFIED line break.
//
// 'justify: true' (function form only) tells the line-break algorithm to
// justify the line BEFORE breaking. Useful when you've found a better
// break point than the optimizer.
//
// Trailing line breaks: a single trailing break at end-of-paragraph is
// IGNORED; more than one creates additional empty lines.

= Markup form

*Date:* 26.12.2026 \
*Topic:* Infrastructure Test \
*Severity:* High

= Function form with justification

#set page(width: 220pt)
#set par(justify: true)

#let jb = linebreak(justify: true)

I have manually tuned the #jb
line breaks in this paragraph #jb
for an _interesting_ result. #jb

= Trailing breaks vs blank lines

Single trailing break (ignored at end of paragraph): \

This text starts a NEW paragraph (blank line above), not an empty line below
the previous text.

Multiple trailing breaks add empty lines: \ \

(Two empty lines above this text.)
