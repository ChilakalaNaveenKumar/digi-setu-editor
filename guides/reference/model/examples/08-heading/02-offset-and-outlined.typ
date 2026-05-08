// Two useful knobs:
//
// 'offset': shifts depth -> level. Useful when reusing a sub-document that
// has its own '= Top heading' but you want it nested under a parent. For
// example, with offset: 1, '= Foo' becomes a level-2 heading.
//
// 'outlined': controls whether a heading appears in '#outline()' AND (by
// default) the PDF bookmark sidebar. The 'bookmarked' field gives you
// independent control over the PDF bookmark.

#set heading(numbering: "1.")

#outline()

= Visible top section

#heading(outlined: false)[Hidden from outline]

This heading exists in the document but does NOT appear in the outline above.

= Another visible section

#set heading(offset: 1)

= Now I'm level-2 (offset shifted me)

#heading(offset: 2, depth: 2)[I'm level-4 because offset 2 + depth 2 = 4]
