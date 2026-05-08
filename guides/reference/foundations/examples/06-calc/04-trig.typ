// sin / cos / tan accept either an angle (90deg, 1rad, ...) or a plain
// number which is then interpreted as radians.
// asin / acos / atan / atan2 RETURN an angle.
// IMPORTANT: atan2(x, y) takes coordinates as (x, y), not (y, x).
// sinh / cosh / tanh take a plain float (radians of hyperbolic angle).

sin(0):           #calc.sin(0)
sin(90deg):       #calc.sin(90deg)
cos(0):           #calc.cos(0)
tan(45deg):       #calc.tan(45deg)

asin(1):          #calc.asin(1)
acos(0):          #calc.acos(0)
atan(1):          #calc.atan(1)
atan2(1, 1):      #calc.atan2(1, 1)

sinh(0):          #calc.sinh(0)
cosh(0):          #calc.cosh(0)
tanh(0.0):        #calc.tanh(0.0)
