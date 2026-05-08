// 'footnote.entry' configures how the LISTING at the bottom of the page
// appears. Set rules MUST be placed BEFORE any page content (entry
// properties must be uniform across each page run -- a sequence of pages
// without an explicit pagebreak).
//
// Most-used entry fields:
//   separator   content   visual divider above the listing
//                           (default: line(length: 30%, stroke: 0.5pt))
//   clearance   length    space between body and the separator (default 1em)
//   gap         length    space between successive entries (default 0.5em)
//   indent      length    left indent of each entry (default 1em)
//
// You can also '#show footnote.entry: ...' to fully customize the
// per-entry rendering.

#set footnote.entry(
  separator: line(length: 40%, stroke: 0.7pt + gray),
  clearance: 1.2em,
  gap: 0.6em,
  indent: 0.5em,
)

#show footnote.entry: it => {
  let loc = it.note.location()
  text(weight: "bold")[#numbering("1.", ..counter(footnote).at(loc))] + " "
  it.note.body
}

#set footnote(numbering: "1")

Footnotes have a custom separator and bold "1." prefixes in their
entries.#footnote[The first.]

A second one#footnote[The second, formatted the same way.] follows.

#lorem(40)#footnote[Comes after some filler text.]
