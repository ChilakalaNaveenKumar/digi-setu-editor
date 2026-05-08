// Demonstrates: 'assert(condition, message: "...")' fails the compile with
// the given message if the condition is false. Produces no output otherwise.
// Use it as a contract check at the start of helper functions.

#let percentile(values, p) = {
  assert(p >= 0 and p <= 100, message: "p must be in [0, 100]")
  assert(values.len() > 0, message: "values must not be empty")
  let idx = calc.floor((p / 100) * (values.len() - 1))
  values.at(idx)
}

p50 of (10, 20, 30, 40, 50) = #percentile((10, 20, 30, 40, 50), 50)
