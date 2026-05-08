// float literals:
//   3.14            decimal
//   1e4 / 1.5e-3    exponential notation
//
// float(value) constructor accepts:
//   bool     -> 0.0 / 1.0
//   int      -> exact for |x| < 2^53, otherwise nearest representable
//   ratio    -> divides by 100% (e.g. float(40%) == 0.4)
//   str      -> parsed in base 10, supports "1e5" exp notation
//   decimal  -> casts (acceptable -- decimal->float is lossy in general but
//                       it's the explicit direction)

3.14:           #3.14
1e4:            #1e4
10/4:           #(10 / 4)

float(false):   #float(false)
float(true):    #float(true)
float(4):       #float(4)
float(40%):     #float(40%)
float("2.7"):   #float("2.7")
float("1e5"):   #float("1e5")
float(decimal("1.234")): #float(decimal("1.234"))
