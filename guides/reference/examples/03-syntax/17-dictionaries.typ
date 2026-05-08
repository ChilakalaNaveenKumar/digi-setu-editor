// Demonstrates: dictionary literals (a: value, b: value, ...).
// Empty dict literal is '(:)' -- bare '()' would be the empty array.
// Access by dot for static keys, or by .at("key") for dynamic keys.

#let metrics = (
  p50: 12.4,
  p99: 98.1,
  errors: 0,
)

p50 latency: #metrics.p50 ms
p99 latency: #metrics.at("p99") ms
Total entries: #metrics.len()
