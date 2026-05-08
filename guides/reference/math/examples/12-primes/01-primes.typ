// 'primes(count)' renders a number of grouped prime marks.
//
// SHORTHAND: apostrophes auto-group and attach to the previous element.
// Importantly, primes do NOT compete with the superscript slot -- they
// move any existing superscript "out of the way" to the next level.

= Apostrophe shorthand

$ a' quad b'' quad c''' quad f'(x) $

= Primes coexisting with superscripts

$ a'''_b = a^'''_b $
// Both forms are equivalent: writing a''' as a base attaches the primes,
// and any further superscript still applies normally.

= Functional notation

$ f'(x) = lim_(h -> 0) (f(x + h) - f(x)) / h $

$ y'' + 3 y' + 2 y = 0 $
