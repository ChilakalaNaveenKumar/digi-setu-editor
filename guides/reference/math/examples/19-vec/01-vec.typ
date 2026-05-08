// 'vec(..elements, delim: ("(", ")"), align: center, gap: 0.2em)'
// renders a column vector.
//
// Note: 'vec' is for typesetting vector COMPONENTS. To typeset a SYMBOL
// representing a vector, use arrow() or bold() on a letter.

= Standard column vector

$ vec(a, b, c) dot vec(1, 2, 3) = a + 2 b + 3 c $

= Custom delimiter

#set math.vec(delim: "[")
$ vec(1, 2) $
#set math.vec(delim: ("(", ")"))

= Right-aligned components

#set math.vec(align: right)
$ vec(-1, 1, -1) $
#set math.vec(align: center)

= Wider gap

#set math.vec(gap: 1em)
$ vec(1, 2) $
#set math.vec(gap: 0.2em)

= Vector SYMBOLS (not components)

$ arrow(v) = vec(v_1, v_2, v_3) $
$ bold(u) + bold(w) = vec(u_1 + w_1, u_2 + w_2) $
