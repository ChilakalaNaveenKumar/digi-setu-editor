// Demonstrates the three forms of code embedded in markup:
//   #identifier        bare variable access
//   #fn(args)          function call
//   #(expression)      arbitrary expression in parentheses
// Use the parenthesised form for binary operators (e.g. #(1 + 2))
// because '#1 + 2' would parse '#1' then literal '+ 2'.

#let build = 1407
Build number: #build.

Word count: #"benchmark report".len()

Sum: #(2 + 3 * 4)
