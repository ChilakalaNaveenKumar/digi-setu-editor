// Demonstrates: destructuring patterns on the LHS of 'let' (and in for-loops
// and assignments). Works on arrays and dictionaries.
// '_' discards a position. '..rest' collects remaining items.

// Array destructuring
#let (head, mid, tail) = ("alpha", "beta", "gamma")
First: #head, Middle: #mid, Last: #tail.

// Discard with '_'
#let (_, only-y, _) = (1, 2, 3)
Kept y: #only-y

// Rest-collect remaining items
#let (first-region, ..other-regions) = ("us-east", "eu-west", "ap-south")
Primary: #first-region. Others count: #other-regions.len().

// Dictionary destructuring (key name = local binding name)
#let (p50, p99) = (p50: 12, p99: 98)
p50=#p50, p99=#p99.

// Dictionary destructuring with rename (key: alias)
#let (p99: tail-latency) = (p99: 98)
Tail latency: #tail-latency.
