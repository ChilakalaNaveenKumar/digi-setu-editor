// 'full: true' shows ALL parent numbers in a nested enum.
//
// With pattern "1.a)":
//   default (full: false):  1)        outer
//                            a)        nested  (just the inner symbol + suffix)
//                            b)        nested
//                           2)        outer
//
//   full: true:             1)        outer
//                            1.a)      nested  (ancestor chain + prefix '.' + suffix ')')
//                            1.b)      nested
//                           2)        outer
//
// 'enum.item(number, body)' lets you explicitly assign numbers programmatically.

#set enum(numbering: "1.a)", full: true)

+ Cook
  + Heat water
  + Add ingredients
+ Eat
  + Quietly
  + Politely

#set enum(numbering: "1.", full: false)

= Programmatic items

#enum(
  enum.item(1)[First step],
  enum.item(5)[Fifth step],
  enum.item(10)[Tenth step],
)

= From a for-loop

#for phase in ("Launch", "Orbit", "Descent") [
  + #phase
]
