// fn.with(...args) -> NEW function with the given arguments PRE-APPLIED.
// Acts like partial application / currying. Subsequent calls supply only
// the remaining arguments.

#let bold-red = text.with(fill: red, weight: "bold")
#bold-red[Highlighted phrase]

#let warn-box = rect.with(stroke: orange + 1pt, inset: 8pt, radius: 4pt)
#warn-box[Pre-styled warning content]

// Partial-applying over positional args also works.
#let add(a, b) = a + b
#let add-five = add.with(5)
add-five(10): #add-five(10)
