// 'none' is the single value of the 'none' type. It signals "absence".
// Properties:
//   - Inserted into a document, it produces NO output (not even a space).
//   - An empty code block '{ }' evaluates to 'none'.
//   - Joining 'none' with any value yields the other value:
//       none + x   ==  x
//       x + none   ==  x
//     This makes 'none' an identity for the '+' join, useful when you want
//     a uniform default for "the empty case" inside fold / join chains.

visible #none here:    visible #none here

none + 7:        #(none + 7)
none + "hi":     #(none + "hi")
none + [*bold*]: #(none + [*bold*])

empty block type:  #type({})
{} == none:        #({} == none)

// Useful pattern: chain content with parbreak() and skip empty cases.
#let render-section(title, body) = {
  if body == none { none } else {
    [== #title] + parbreak() + body
  }
}

#render-section("Intro", [Hello.])
#render-section("Skipped", none)
#render-section("Outro", [Goodbye.])
