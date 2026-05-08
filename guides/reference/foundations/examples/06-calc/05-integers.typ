// Integer-only utilities.
// fact(n)         -> n!
// perm(n, k)      -> n! / (n-k)!  (ordered selections)
// binom(n, k)     -> n choose k   (unordered selections)
// gcd(a, b)       -> greatest common divisor
// lcm(a, b)       -> least common multiple
// even(n) / odd(n) -> bool. Both are usable as filter callbacks.

fact(5):                    #calc.fact(5)
perm(5, 3):                 #calc.perm(5, 3)
binom(10, 3):               #calc.binom(10, 3)
gcd(24, 36):                #calc.gcd(24, 36)
lcm(4, 6):                  #calc.lcm(4, 6)

even(4):                    #calc.even(4)
odd(4):                     #calc.odd(4)
range(10).filter(calc.even): #range(10).filter(calc.even)
