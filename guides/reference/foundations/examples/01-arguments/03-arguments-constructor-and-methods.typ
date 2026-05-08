// Demonstrates: the 'arguments(...)' constructor builds an arguments value
// in place. It captures everything you pass exactly as a function would.
// Methods on the result:
//   .pos()      -> array of positional args
//   .named()    -> dictionary of named args
//   .at(idx)    -> single positional arg by index (alias for .pos().at(idx))
//   .at("key")  -> single named arg by name   (alias for .named().at("key"))

#let bundle = arguments("alpha", "beta", region: "us-east", build: 1407)

Positional: #bundle.pos()
Named: #bundle.named()
First positional: #bundle.at(0)
Named "build": #bundle.at("build")

// And spread back into a function call.
#let join-pos(..args) = args.pos().join(" + ")
Joined: #join-pos(..bundle)
