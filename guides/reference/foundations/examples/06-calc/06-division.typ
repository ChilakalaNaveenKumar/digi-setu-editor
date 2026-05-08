// Four division-related functions; all differ on negative inputs.
//
//   rem(a, b)         -> remainder; SAME sign as a; |result| < |b|
//   rem-euclid(a, b)  -> remainder; ALWAYS in [0, |b|)
//   div-euclid(a, b)  -> quotient that pairs with rem-euclid (rounds
//                        toward -inf). result * b + rem-euclid(a, b) = a.
//   quo(a, b)         -> floored integer division. ALWAYS returns int.

rem(7, 3):              #calc.rem(7, 3)
rem(-7, 3):             #calc.rem(-7, 3)
rem-euclid(-7, 3):      #calc.rem-euclid(-7, 3)
div-euclid(-7, 3):      #calc.div-euclid(-7, 3)
quo(14, 5):             #calc.quo(14, 5)
quo(-14, 5):            #calc.quo(-14, 5)
