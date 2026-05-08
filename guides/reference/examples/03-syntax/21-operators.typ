// Demonstrates: arithmetic, comparison, logical, and membership operators.
// Higher-precedence operators bind tighter (multiplication before addition,
// comparison before logical, etc.). Use parentheses when in doubt.

Arithmetic: #(2 + 3), #(10 - 4), #(6 * 7), #(15 / 4)
Negation: #(-5), unary plus (no-op): #(+5)
Comparison: #(2 < 3), #(2 == 2), #(3 != 4), #(5 >= 5)
Logical: #(true and false), #(true or false), #(not true)
Membership: #("y" in "yes"), #("z" in ("x", "y"))
String concat with '+': #("build-" + "1407")
Array concat: #((1, 2) + (3, 4))
