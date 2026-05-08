// Demonstrates: anonymous functions (closures).
// Syntax:  (params) => body          single-expression body
//          (params) => { ... }       multi-statement body
// A closure with one parameter and an arg-less body can also be:
//          name => body
// Named functions are sugar:  '#let f(x) = ...'  ==  '#let f = x => ...'.

#let square = x => x * x
#let add = (a, b) => a + b
#let pluralize = (word, n) => {
  if n == 1 { word } else { word + "s" }
}

square(7) = #square(7)
add(3, 4) = #add(3, 4)
pluralize("build", 1) = #pluralize("build", 1)
pluralize("build", 5) = #pluralize("build", 5)
