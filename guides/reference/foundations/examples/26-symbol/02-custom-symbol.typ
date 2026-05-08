// 'symbol(...variants)' constructs a custom symbol.
//
// Each variant is either:
//   - a single string -> the modifier-less default
//   - an array (modifiers, glyph) where 'modifiers' is a dot-separated
//     string of modifier names and 'glyph' is the displayed string
//
// Resolving a chained access like 'envelope.stamped.pen' picks the variant
// whose modifier set is the smallest superset of {stamped, pen}.

#let envelope = symbol(
  "🖂",                        // default (no modifiers)
  ("stamped",       "🖃"),
  ("stamped.pen",   "🖆"),
  ("lightning",     "🖄"),
  ("fly",           "🖅"),
)

#envelope            \
#envelope.stamped    \
#envelope.stamped.pen \
#envelope.lightning  \
#envelope.fly
