// Define a function with 'let name(params) = body':
//   - positional params: just a name
//   - named params with default: 'name: default-expr'
//   - argument sink: '..rest'  (must be last)
// The body is any expression; if it's a code block { ... }, the return value
// is the joined value of all top-level expressions in the block.

#let alert(body, fill: red) = {
  set text(white)
  set align(center)
  rect(
    fill: fill, inset: 8pt, radius: 4pt,
    [*Warning:* #body],
  )
}

#alert[Danger ahead]
#alert(fill: blue)[Notice: track maintenance scheduled.]

// Anonymous (arrow) functions. Single-param parens are optional.
#let double = x => x * 2
#let add = (a, b) => a + b
#let sum = (..nums) => nums.pos().sum()

double(7):    #double(7)
add(2, 3):    #add(2, 3)
sum(1, 2, 3): #sum(1, 2, 3)

// Early return.
#let abs-pos(n) = {
  if n < 0 { return -n }
  n
}
abs-pos(-5): #abs-pos(-5)
