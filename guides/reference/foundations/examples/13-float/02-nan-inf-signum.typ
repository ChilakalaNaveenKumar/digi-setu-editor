// Special values are exposed on the type:
//   float.nan   -- NaN (not a number)
//   float.inf   -- positive infinity (use -float.inf for negative)
//
// Predicates and sign:
//   float.is-nan(x)       -> bool. Use this; x == float.nan is ALWAYS false.
//   float.is-infinite(x)  -> bool. True for both +inf and -inf.
//   x.signum()            -> 1.0 for positive (incl. +0.0),
//                           -1.0 for negative (incl. -0.0),
//                           float.nan for NaN.

is-nan(0):                   #float.is-nan(0)
is-nan(float.nan):           #float.is-nan(float.nan)
nan == nan (always false):   #(float.nan == float.nan)
is-infinite(1):              #float.is-infinite(1)
is-infinite(float.inf):      #float.is-infinite(float.inf)
is-infinite(-float.inf):     #float.is-infinite(-float.inf)

(5.0).signum():              #(5.0).signum()
(-5.0).signum():             #(-5.0).signum()
(0.0).signum():              #(0.0).signum()
float.nan.signum():          #float.nan.signum()
