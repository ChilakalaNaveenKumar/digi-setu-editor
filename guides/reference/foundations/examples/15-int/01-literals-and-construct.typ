// 'int' is a 64-bit signed whole number.
// Range: -9223372036854775808 .. 9223372036854775807.
// Values larger than the max literal are parsed as 'float' instead.
//
// Bases: a leading '0x' / '0o' / '0b' is hex / octal / binary.
// Negative ints are the negation of a positive literal: '-1' is '-(1)'.
//
// 'int(value)' converts:
//   bool    -> 0 or 1
//   float   -> truncate toward 0   (2.7 -> 2,  -2.7 -> -2)
//   decimal -> truncate toward 0   (decimal("3.8") -> 3)
//   str     -> parse as base 10    ("27" -> 27)

decimal:    #(1 + 2)
hex 0xff:   #0xff
octal 0o10: #0o10
binary 0b1001: #0b1001

#int(true):           #int(true)
#int(false):          #int(false)
#int(2.7):            #int(2.7)
#int(-2.7):           #int(-2.7)
#int(decimal("3.8")): #int(decimal("3.8"))
#int("27") + #int("4") = #(int("27") + int("4"))
