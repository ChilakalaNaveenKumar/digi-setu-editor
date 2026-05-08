// pow accepts int / float / decimal as base. If base is decimal,
// the exponent must be an int.
// sqrt is the 2-root. root(x, n) is the real n-th root; if x < 0
// then n must be odd.
// exp is e^x. log defaults to base 10; pass 'base:' to change it.
// ln is natural log. Constants: calc.pi, calc.tau, calc.e, calc.inf.

pow(2, 10):           #calc.pow(2, 10)
pow(2.5, 2):          #calc.pow(2.5, 2)
sqrt(16):             #calc.sqrt(16)
root(27.0, 3):        #calc.root(27.0, 3)
exp(1):               #calc.exp(1)
log(1000):            #calc.log(1000)
log(8, base: 2.0):    #calc.log(8, base: 2.0)
ln(calc.e):           #calc.ln(calc.e)
