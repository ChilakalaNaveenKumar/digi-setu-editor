// 'numbering(pattern, ..numbers) -> any' applies a numbering pattern (or a
// function) to a sequence of non-negative integers.
//
// PATTERN: a string built from
//   - counting symbols: each gets replaced by the next number
//   - prefixes: anything between counting symbols (printed as-is, before the
//     digit they precede)
//   - suffix: everything AFTER the LAST counting symbol (printed once at the end)
//
// Common counting symbols and the alphabet they cycle through:
//   "1"  arabic   1, 2, 3, ...
//   "a"  latin    a, b, c, ..., z, aa, ab, ...
//   "A"  latin    A, B, C, ..., Z, AA, AB, ...
//   "i"  roman    i, ii, iii, iv, ...
//   "I"  roman    I, II, III, IV, ...
//   "*"  symbols  * † ‡ § ¶ ‖ then doubled (** etc.) once exhausted
//   "α", "Α", "一", "壹", "あ", "い", "ア", "イ", "א", "가", "ㄱ", "①", "⓵",
//   plus several Arabic-script numerals
//
// FUNCTION form: pass a function instead of a string. It receives each number
// as a separate positional argument. Useful for fully custom logic.

= Pattern strings

#numbering("1.1)", 1, 2, 3) \
#numbering("1.a.i", 1, 2) \
#numbering("I -- 1", 12, 2) \
#numbering("*", 1) #numbering("*", 2) #numbering("*", 6) #numbering("*", 7)

= More numbers than counting symbols

If you pass MORE numbers than there are counting symbols in the pattern,
the LAST counting symbol (with its prefix) is REPEATED for each extra:

#numbering("1.", 1, 2, 3, 4) \
#numbering("1.a", 1, 2, 3, 4)

= Function form

#let unary(..nums) = "|" * nums.pos().last()
#numbering(unary, 3) \
#numbering(unary, 7)

= Unified ergonomics

The point of 'numbering' as a callable wrapper is that consumers (heading,
enum, figure...) can take EITHER a pattern OR a function and treat them
uniformly. You rarely need to call 'numbering(...)' yourself outside of
custom show rules and counters.
