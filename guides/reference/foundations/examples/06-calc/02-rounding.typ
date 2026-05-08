// floor / ceil / trunc always return an int.
// round returns the SAME numeric type as the input (int -> int,
// float -> float, decimal -> decimal). Half values round AWAY from zero.
// round takes a named 'digits:' argument:
//   positive -> decimal places kept
//   negative -> significant integer digits zeroed before the decimal point
// fract returns the fractional remainder, same numeric type as input.

floor(3.9):                  #calc.floor(3.9)
ceil(3.1):                   #calc.ceil(3.1)
trunc(-3.7):                 #calc.trunc(-3.7)
fract(3.25):                 #calc.fract(3.25)

round(2.5):                  #calc.round(2.5)
round(3.1415, digits: 2):    #calc.round(3.1415, digits: 2)
round(3333.45, digits: -2):  #calc.round(3333.45, digits: -2)
