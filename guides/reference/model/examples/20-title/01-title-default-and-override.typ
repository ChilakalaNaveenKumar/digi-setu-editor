// 'title()' is the document's MAIN TITLE. There should be at most ONE per
// document. Distinct from level-1 headings, which are top-level *sections*.
//
// Two ways to populate it:
//   1. Pass content directly:
//        #title[My Paper]
//   2. Omit the body (or pass 'auto') and rely on document.title:
//        #set document(title: [My Paper])
//        #title()
//      The second form is preferred when the same string should appear both
//      as the visible page title AND as the PDF metadata title.
//
// Pitfall: '#title()' with no body and no preceding 'set document(title: ...)'
// will ERROR. Either set the document title first or pass a body inline.
//
// HTML export note: 'title' becomes <h1>, while level-1 headings become <h2>.

#set document(title: [Course ABC, Homework 1])

#title()  // pulls from document.title above

= Introduction
This section is a level-1 HEADING, not a title. In HTML export it would be
<h2>, while the title above would be <h1>.

#pagebreak()

#title[Override: A Different Visible Title]

The visible title here was overridden inline, but the PDF metadata still says
"Course ABC, Homework 1" because the `set document` rule was not changed.
