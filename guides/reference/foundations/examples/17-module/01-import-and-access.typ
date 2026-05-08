// Three common import shapes:
//
//   #import "file.typ"            // bind module to its filename stem
//                                 // -> here that would be 'helpers'
//
//   #import "file.typ" as h       // bind module to an explicit local name
//
//   #import "file.typ": a, b      // bring specific definitions into scope
//
// You access module members with '.' (field access notation):
//   h.add(2, 3)
//
// Use the explicit 'as' form when the filename stem is not a clean identifier
// (digits, dashes, dots, underscores at the start, etc.).

#import "helpers.typ" as h
#import "helpers.typ": sub

h.add(2, 5):    #h.add(2, 5)
h.pi-approx:    #h.pi-approx
sub(10, 4):     #sub(10, 4)
