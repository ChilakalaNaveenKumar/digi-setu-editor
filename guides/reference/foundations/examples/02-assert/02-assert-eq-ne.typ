// Demonstrates:
//   assert.eq(a, b, message: "...")  fails if a != b
//   assert.ne(a, b, message: "...")  fails if a == b
// On failure, the default error message includes the actual values, which is
// usually more useful than a hand-rolled message string. Provide a custom
// 'message:' only when the values alone would not explain the failure.

#let total(parts) = parts.fold(0, (acc, n) => acc + n)

#assert.eq(total((1, 2, 3, 4)), 10)
#assert.ne(total((1, 2, 3, 4)), 11)

Sum is #total((1, 2, 3, 4)). Both assertions held.
