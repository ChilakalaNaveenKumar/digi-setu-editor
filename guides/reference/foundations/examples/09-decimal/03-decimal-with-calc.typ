// calc functions that work on decimal:
//   abs, min, max, clamp                               -> return decimal
//   floor, ceil, trunc                                 -> return INT
//   round (with digits:), fract                        -> return decimal
//   pow with INTEGER exponent                          -> return decimal
//
// Functions that REQUIRE float (sqrt, root, sin/cos/tan, log, ln, exp,
// pow with non-int exponent, etc.) refuse decimal input. Cast with
// float(...) if you accept the precision loss.

#let x = decimal("-3.7849")

abs:                 #calc.abs(x)
floor:               #calc.floor(x)
ceil:                #calc.ceil(x)
trunc:               #calc.trunc(x)
round to 2 digits:   #calc.round(x, digits: 2)
fract:               #calc.fract(x)
pow(2, 5) decimal:   #calc.pow(decimal("2"), 5)
clamp [-1, 1]:       #calc.clamp(x, decimal("-1"), decimal("1"))
