// 'pagebreak(weak: false, to: none)' forces a manual page break.
//
// 'weak: true' skips if the current page is already empty.
// 'to: "even"' / "odd"' inserts a blank intermediate page if needed
//   so the next non-empty page lands on an even/odd page number.
//
// pagebreak() may NOT be used inside containers (block, box, etc.).

#set page(height: 80pt)

The next page contains more details.
#pagebreak()

== More details

In 1984, the first ...

#pagebreak(to: "odd")

This page is forced to be ODD-numbered. Typst inserted an empty even
page if needed so this content lands on an odd page.

#pagebreak()
#pagebreak(weak: true)
// Above: the first pagebreak ends the page; the second is weak and
// does NOTHING because we're already on a fresh empty page.

This isn't on a fresh empty page -- the weak break collapsed.
