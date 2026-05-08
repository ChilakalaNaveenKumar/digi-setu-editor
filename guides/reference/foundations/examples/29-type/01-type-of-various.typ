// 'type(value)' returns the type of any value. The returned value IS the
// type (you can compare it directly: 'type(x) == int').
//
// Important: every document element returns 'content' from type(). To
// distinguish "this is a heading" from "this is a paragraph", use
// 'value.func()' instead -- see example 02.
//
// 'none' and 'auto' are unusual: their TYPE has no name binding. To test
// for them you compare the VALUE directly (x == none, y == auto), NOT
// 'type(x) == ???'.

#let x = 10

type(10):           #type(10)
type(14.7):         #type(14.7)
type("hello"):      #type("hello")
type(<glacier>):    #type(<glacier>)
type([Hi]):         #type([Hi])
type(x => x + 1):   #type(x => x + 1)

// type(int) and type(type) -- types ARE values.
type(int):          #type(int)
type(type):         #type(type)

// type(x) == int dispatch.
#if type(x) == int [
  #x is an integer.
] else [
  #x is some other type.
]

// 'none' / 'auto' don't have a name binding; compare the value.
#let v = none
v == none:          #(v == none)
