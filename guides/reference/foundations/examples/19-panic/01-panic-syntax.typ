// 'panic(value, ...)' STOPS the compile and shows the values to the user
// in the CLI as an error. Values are not rendered into the document.
//
// Multi-arg form: values are formatted via 'repr' and joined with ", '.
//
// Verified panic output (separately tested):
//
//   #panic("this is wrong")
//     -> error: panicked with: "this is wrong"
//
//   #panic("bad config", (port: 8080, retries: 3))
//     -> error: panicked with: "bad config", (port: 8080, retries: 3)
//
// Use 'panic' only for "this should be impossible" / unrecoverable internal
// invariants. For input validation, prefer 'assert(...)' / 'assert.eq(...)' --
// they read better at the call site and produce more useful messages.
//
// Below is a SAFE wrapper that would panic only on bad input. We exercise
// only the good path so this file compiles cleanly.

#let safe-divide(a, b) = {
  if b == 0 {
    panic("divide by zero", a, b)
  } else {
    a / b
  }
}

10 / 2 = #safe-divide(10, 2)
10 / 4 = #safe-divide(10, 4)

// safe-divide(10, 0) would print:
//   error: panicked with: "divide by zero", 10, 0
