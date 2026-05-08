// Demonstrates: conditional and loop control flow.
// 'if', 'for', 'while' are EXPRESSIONS -- they yield (joined) values. Each
// branch body can be a code block { ... } or a content block [ ... ].
// 'break' exits the nearest loop; 'continue' skips to the next iteration.

#let status = "green"

// if-else as an expression yielding a string
#let label = if status == "green" { "OK" } else if status == "amber" { "WARN" } else { "FAIL" }
Status: #label

// for over a range-like array, joining content blocks
#for n in (1, 2, 3) [- Stage #n complete \ ]

// for over string graphemes
#for ch in "abc" [#ch /]

// while loop with break, accumulating values into an array
#let collected = (
  while true {
    let n = 7
    n
    break
  }
)
Collected: #collected
