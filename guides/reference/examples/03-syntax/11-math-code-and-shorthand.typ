// Demonstrates:
//   - ASCII shorthands in math mode: ->  =>  !=  <=  >=
//   - embedding a code expression inside math with '#(...)' or '#fn(...)'
//   - field access on a symbol value inside math (arrow.r.long)

$ a -> b $
$ x != y, x <= y, x >= z $
$ f: A => B $
$ arrow.r.long $

#let edge = 0.4cm
$ #rect(width: edge, height: edge) "<-- inline shape" $
