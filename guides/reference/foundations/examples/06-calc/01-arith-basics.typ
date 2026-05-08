// Basic numeric helpers. abs/min/max/clamp accept int, float, decimal,
// and dimension-like types (length, angle, ratio, fraction) where it
// makes sense. min/max are variadic: any number of args >= 1.
// clamp(value, lo, hi) is inclusive on both ends.

abs(-12):           #calc.abs(-12)
abs(5pt - 2cm):     #calc.abs(5pt - 2cm)
min(7, 2, 9, -3):   #calc.min(7, 2, 9, -3)
max(7, 2, 9, -3):   #calc.max(7, 2, 9, -3)
clamp(15, 0, 10):   #calc.clamp(15, 0, 10)
clamp(-1, 0, 10):   #calc.clamp(-1, 0, 10)
clamp(5, 0, 10):    #calc.clamp(5, 0, 10)
