// Subtle but important distinction:
//
//   = Heading <a>             // <a> ENDS the heading and attaches to the
//                             // heading element itself. Equivalent to
//                             // '#heading[Heading] <a>'.
//                             // -> @a / #ref(<a>) works as expected.
//
//   = Heading #label("b")     // #label("b") is INSIDE the heading body.
//                             // Equivalent to '#heading[Heading #label("b")]'.
//                             // It attaches to the heading's text/body
//                             // content, NOT to the heading element.
//                             // -> @b / #ref(<b>) FAILS with
//                             //    "error: cannot reference text".
//
// Rule of thumb: to make a heading (or any element) referenceable, put the
// label OUTSIDE it using the angle-bracket form, after the element.
//
// Labels currently only attach in MARKUP mode, not in code mode.

#set heading(numbering: "1.")

= Section A <sec-a>

= Section B #label("sec-b-inside-body")

See @sec-a -- this works because the label is on the heading element.

The label "sec-b-inside-body" exists in the document but is attached to the
heading's body text, so '#ref' to it would error. Use the '<sec-b>' form
after the heading instead if you want to reference it.
