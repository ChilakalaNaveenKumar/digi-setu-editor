// 'super(body, typographic: true, baseline: auto, size: auto)' renders text
// in superscript. Mirror image of 'sub'.
//
// Note: footnote markers are also rendered with 'super' under the hood.
// 'set super(...)' inside the document affects them.
//
// For SYNTHESIZED superscripts only (typographic: false OR font lacks sups):
//   baseline   font metric or fallback -0.5em
//                 NOTE: NEGATIVE values raise the text (it's a downward shift)
//   size       font metric or fallback 0.6em

= Markup-style use

1#super[st] try \
H#sub[2]O on day #super[3] \
x#super[2] + y#super[2] = z#super[2]

= Typographic vs synthesized

Typographic: N#super(typographic: true)[1] \
Synthesized: N#super(typographic: false)[1]

= Custom metrics on synthesized superscripts

Default:           N#super(typographic: false)[1] \
baseline -0.7em:   N#super(typographic: false, baseline: -0.7em)[1] \
size 0.5em:        N#super(typographic: false, size: 0.5em)[1]

= Affects footnote markers too

#set super(typographic: false, size: 0.5em)
Some text.#footnote[The marker uses our super-set rule.]

#lorem(20)
