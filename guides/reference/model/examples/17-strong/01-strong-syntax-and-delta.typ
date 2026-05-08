// 'strong(body, delta: int = 300)' increases the font weight by 'delta'.
//
// Markup shorthand: enclose content in asterisks '*..*'. Same word-boundary
// rule as emph -- to bold PART of a word, call the function.
//
// 'delta' is the WEIGHT INCREMENT, not the absolute weight. 300 means
// "bump roughly from regular (400) to bold (700)". Setting delta: 0
// disables the visual effect (useful for show-rule-driven custom styling).

This is *strong.* \
This is #strong[too.] \
Inside-word: ex#strong[trao]rdinary

#show strong: set text(fill: red)
And this is *evermore* (red because of the show rule).

#set strong(delta: 0)
With delta: 0, *no visual effect* -- but the strong element still exists,
so show rules and queries still see it.

#set strong(delta: 600)
#set text(fill: black)  // reset color
With a big delta: 600, this *gets ultra-bold* if the font supports it.
