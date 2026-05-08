// Demonstrates: 'let' binds names. Two forms:
//   let name = expr               variable binding
//   let name(params...) = expr    named function (sugar for: let name = (...) => expr)
// A 'let' without '= ...' initialises the binding to none.

#let region = "us-east-1"
#let unset
#let circle-area(r) = calc.pi * r * r

Region: #region
Unset is none? #(unset == none)
Area for r=3: #circle-area(3)
