// Three call-site syntaxes:
//   1. Standard: f(positional1, positional2, name1: v1, name2: v2)
//   2. Trailing content blocks: f(name: v)[content1][content2]
//      Each [..] block becomes an additional positional argument.
//   3. No-paren shorthand: f[content1][content2]
//      When there are NO normal arguments, you can drop the empty (). Only
//      the trailing content blocks remain.
//
// Names of named arguments must come AFTER all positional args.

// Standard call.
#list([Apple], [Banana], [Cherry])

// Named arg + trailing content blocks.
#enum(start: 2, [Skip], [Then], [End])

// Equivalent: trailing content blocks instead of positional args.
#enum(start: 2)[Skip][Then][End]

// No-paren shorthand (no normal args, only trailing blocks).
#list[Red][Green][Blue]
