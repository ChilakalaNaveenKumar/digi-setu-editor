// norm(p: 2.0, ..values) -> the p-norm of the values.
//   p = 1   -> sum of absolute values (Manhattan / L1)
//   p = 2   -> Euclidean (default)
//   p = N   -> generalized Lp norm
// Module also exposes constants: pi, tau, e, inf.
// (calc.tau == 2 * calc.pi.)

norm(3, 4):             #calc.norm(3, 4)
norm(p: 1, 1, 2, 3):    #calc.norm(p: 1, 1, 2, 3)
norm(p: 3, 1, 2):       #calc.norm(p: 3, 1, 2)

pi:                     #calc.pi
tau:                    #calc.tau
e:                      #calc.e
inf > 1.0e10:           #(calc.inf > 1.0e10)
