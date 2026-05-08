// Demonstrates: '..name' in a function parameter list creates an
// "argument sink" -- a single binding of type 'arguments' that collects
// every excess positional AND named argument the caller passes.
// Use .pos() to access the positional ones, .named() for the named ones.

#let report(title, ..extras) = {
  let positional-count = extras.pos().len()
  let named-count = extras.named().len()
  [*#title* -- captured #positional-count positional, #named-count named]
}

#report("Build", "alpha", "beta", "gamma", region: "us-east", retries: 3)
