// Demonstrates: identifier rules.
// Allowed chars: letters, digits, '-', '_'. Must start with a letter or '_'.
// Recommended convention: kebab-case (lowercase, hyphen-separated).
// Hyphens inside identifiers are not subtraction; whitespace disambiguates.

#let build-number = 1407
#let _internal-cache = ("hits": 12, "misses": 3)
#let π = calc.pi

Build #build-number, cache hit rate #_internal-cache.hits.
Half of pi is #(π / 2).
