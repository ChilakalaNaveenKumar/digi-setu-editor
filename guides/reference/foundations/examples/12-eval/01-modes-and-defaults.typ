// 'eval(source, mode: "code", scope: (:))' parses and evaluates a string of
// Typst source at compile time.
//
// mode (named, default "code"):
//   "code"    -- evaluate as if AFTER a '#'. Returns the expression's value.
//   "markup"  -- evaluate as if it were a Typst markup file. Returns content.
//   "math"    -- evaluate as math content. Returns content.
//
// USE AS LAST RESORT. eval is opaque to the formatter, breaks IDE
// completion, and has no scope guard. Prefer real bindings/functions.

code:   #eval("1 + 1")
length: #eval("(1, 2, 3, 4)").len()
markup: #eval("*Bold!* and _italic_", mode: "markup")
math:   #eval("a^2 + b^2 = c^2", mode: "math")
