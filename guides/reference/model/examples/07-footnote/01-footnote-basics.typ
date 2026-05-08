// 'footnote(body)' inserts a numbered superscript that links to a note at
// the bottom of the same page. Notes auto-number sequentially across the
// document and break across pages.
//
// 'body' is normally content. It can ALSO be a 'label' -- in that case the
// new footnote points to an existing footnote with that label (no new
// numbered note is created).
//
// Markers attach to the PRECEDING WORD. To force whitespace before a marker,
// use string " " or '#h(0.5em)'.
//
// 'set footnote(numbering: ...)' lets you change the marker style:
//   "1"   default arabic
//   "i"   roman
//   "*"   symbols (* † ‡ § ¶ ‖, then doubled)

Check the docs for more details.#footnote[https://typst.app/docs] The
marker attached to the previous word.

Forced spacing before:#h(0.5em)#footnote[Now there's space before me.]

= Custom numbering

#set footnote(numbering: "*")

Footnotes:
#footnote[Star],
#footnote[Dagger],
#footnote[Double dagger]

= Multiple references to the same footnote

You can edit Typst online.#footnote[https://typst.app/app] <fn>

Checkout Typst's website. @fn

And the online app. #footnote(<fn>)
