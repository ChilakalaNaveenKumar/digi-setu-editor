// Every document element has type 'content'. type() alone can't tell you
// "is this a heading or a paragraph?". For that, use 'value.func()' which
// returns the element function (heading, par, list, ...).
//
// Common pattern: a show-rule handler receives content and dispatches on
// '.func()' to handle different element kinds.

#let h    = [= My Heading]
#let p    = [Just a paragraph.]
#let lst  = [- one
- two]

type(heading content):  #type(h)
type(paragraph content): #type(p)
type(list content):     #type(lst)

// All three are 'content'. To DIFFERENTIATE them, use .func():
h.func():    #repr(h.func())
p.func():    #repr(p.func())
lst.func():  #repr(lst.func())

// Equality on funcs lets you dispatch:
is heading:  #(h.func() == heading)
is list:     #(lst.func() == list)
