// 'underline()' / 'overline()' draw a horizontal line under/over content.
// (These are MATH module entries -- distinct from text 'underline'/'overline'.)
//
// Brace / bracket / paren / shell variants ALSO accept an OPTIONAL
// 'annotation' content that floats below (under*) or above (over*).

= Plain lines

$ underline(1 + 2 + dots + 5) $

$ overline(1 + 2 + dots + 5) $

= Braces with annotations

$ underbrace(0 + 1 + dots.c + n, n + 1 "numbers") $

$ overbrace(a_1 + a_2 + dots + a_n, "n terms") $

= Brackets, parens, tortoise shells

$ underbracket(0 + 1 + dots.c + n, n + 1 "numbers") $

$ overbracket(0 + 1 + dots.c + n, n + 1 "numbers") $

$ underparen(0 + 1 + dots.c + n, n + 1 "numbers") $

$ overparen(0 + 1 + dots.c + n, n + 1 "numbers") $

$ undershell(0 + 1 + dots.c + n, n + 1 "numbers") $

$ overshell(0 + 1 + dots.c + n, n + 1 "numbers") $
