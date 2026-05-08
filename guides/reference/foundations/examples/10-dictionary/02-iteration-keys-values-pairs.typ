// Introspection methods, all returning ARRAYS in INSERTION ORDER:
//   .keys()    -> array of strings
//   .values()  -> array of values
//   .pairs()   -> array of [key, value] pairs (each pair is a 2-array)
//
// Iteration in 'for' loops uses destructuring:
//   for (k, v) in dict.pairs() { ... }

#let stats = (
  build:  3142,
  region: "us-east",
  retries: 2,
)

keys:   #stats.keys()
values: #stats.values()

#for (k, v) in stats.pairs() [
  - *#k* = #v
]
