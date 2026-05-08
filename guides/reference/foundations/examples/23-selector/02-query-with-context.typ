// 'query(selector)' returns the array of content elements matching the
// selector. It depends on the document's final layout, so it must be called
// inside a 'context { ... }' block.
//
// Demonstrated below:
//   - bare label and bare element-function as selectors
//   - explicit selector(...) constructor
//   - .or to unify two element-function selectors
//   - .before to bound the search by document position
//
// Output is the count + the .body of each match, so we don't dump huge reprs.

#set heading(numbering: "1.")

= Intro <intro>

= Chapter 1
== Sub a
== Sub b

= Chapter 2 <ch2>
== Sub c

= Chapter 3

#context {
  let titles(arr) = arr.map(h => h.body).join(" | ")

  let lvl1 = heading.where(level: 1)
  let lvl12 = lvl1.or(heading.where(level: 2))
  let before-ch2 = lvl1.before(<ch2>, inclusive: false)
  let by-label = selector(<intro>)

  [
    Total level-1 headings: #query(lvl1).len() \
    Level 1 OR 2: #query(lvl12).len() \
    Level-1 before <ch2> (exclusive): #titles(query(before-ch2)) \
    selector(<intro>) matched: #query(by-label).len()
  ]
}
