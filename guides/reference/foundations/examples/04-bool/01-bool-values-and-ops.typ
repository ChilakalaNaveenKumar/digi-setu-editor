// The bool type has exactly two values: true and false.
// Boolean values are produced by:
//   - the literals  true / false
//   - comparison operators:  ==  !=  <  <=  >  >=
//   - the membership operator:  in   (also: not in)
//   - the logical operators:  not, and, or
// Booleans drive 'if' / 'while' conditions and 'assert(...)' checks.

literal true:  #true
literal false: #false

3 < 5:          #(3 < 5)
3 == 4:         #(3 == 4)
"a" in "alpha": #("a" in "alpha")

not true:        #(not true)
true and false:  #(true and false)
true or false:   #(true or false)

#let connected = true
#if connected [Status: online] else [Status: offline]
