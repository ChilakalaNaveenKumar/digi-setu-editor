// PAGE-LEVEL columns + page references.
//
// 'set page(columns: N)' creates real page columns: pagebreaks, footnotes,
// and line numbering all keep working (unlike '#columns(N)[...]').
//
// 'set page(numbering: ..., supplement: ...)' lets you customize page refs.

#set page(columns: 2, height: 200pt, numbering: "1.", supplement: [p.])

= Introduction <intro>

The "intro" label is on this page. We can reference its page number
elsewhere as 'page X' or with a custom supplement.

#lorem(60)

We are on #ref(<intro>, form: "page")
(the page-form ref includes the supplement we set above).

#colbreak()

= Methods

Switching to the second column. Pagebreaks across columns still work
(try the next page).

#lorem(60)
