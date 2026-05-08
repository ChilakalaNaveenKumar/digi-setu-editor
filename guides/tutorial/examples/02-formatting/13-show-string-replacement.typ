// Demonstrates: show rule with a string selector. Every occurrence of
// the literal string is replaced by the result of the callback function.
// Syntax: '#show "TARGET": handler'. The handler receives the matched
// content as its argument.

#show "DigiSetu": name => box[
  #box(image("_assets/sample.png", height: 0.7em))
  #name
]

The DigiSetu pipeline now ships nightly builds.
DigiSetu is maintained by the platform team.
