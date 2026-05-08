// 'document' is the implicit root element of every Typst document. You never
// CONSTRUCT one yourself -- you only configure it via 'set document(...)' to
// embed METADATA into the exported PDF (title, authors, description, keywords,
// creation date).
//
// Settable fields:
//   title       none | content    PDF window title (PLAIN TEXT only after conversion)
//   author      str   | array<str>
//   description none | content
//   keywords    str   | array<str>
//   date        none | auto | datetime
//                  - auto: current date (default)
//                  - none: omit creation date entirely (useful for reproducible PDFs)
//                  - datetime: a specific datetime
//
// Important rule: 'set document(...)' must be at TOP LEVEL (or inside a top-level
// container that is not a layout container). It cannot live inside e.g. a #grid,
// #figure, #block, etc. -- the compiler errors with
//   "set rule must not occur inside of any layout container".

#set document(
  title: [Typst Agent: Model Reference],
  author: ("Digi Setu",),
  description: [Compile-verified guides for the Typst Model module.],
  keywords: ("typst", "model", "reference", "documentation"),
  date: datetime(year: 2026, month: 5, day: 1),
)

= About this PDF

This file's body is short on purpose: the interesting bits are in the PDF
metadata, not on the page. After compiling, inspect the file's properties in
your viewer (or run `pdfinfo` if you have it installed) -- you'll see the
title, author, description, keywords, and creation date set above.

The visible content here exists only to give the PDF at least one page.
