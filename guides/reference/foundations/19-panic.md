# `panic` — abort the compile with a message

`panic(value, ...)` immediately fails the compile and prints all `value`s to the user as an error message. It produces no document output. Multiple values are formatted via `repr` (where needed) and joined with `, `.

## Signature

```
panic(..values: any) -> ! (never returns)
```

`values` is variadic and accepts any Typst value.

## When to reach for it

- **`assert(...)` / `assert.eq(...)`** — preferred for validating function arguments and invariants. Better default messages, more idiomatic.
- **`panic(...)`** — for "this should be impossible" / unrecoverable internal-state errors, where you want to dump arbitrary context (a config dict, the offending args, etc.) into the error message.

A common pattern:

```typst
#let safe-divide(a, b) = {
  if b == 0 { panic("divide by zero", a, b) } else { a / b }
}
```

## Verified error output

| Call                                                | Error                                                     |
| --------------------------------------------------- | --------------------------------------------------------- |
| `#panic("this is wrong")`                           | `panicked with: "this is wrong"`                          |
| `#panic("bad config", (port: 8080, retries: 3))`    | `panicked with: "bad config", (port: 8080, retries: 3)`   |

Both verified against `typst 0.14.2` in a scratch compile.

## Pitfalls

- **There is no try/catch in Typst.** Once `panic` fires, the compile aborts. You can't recover.
- Don't use `panic` for messages you want to *display* in the document; the values go to stderr only.
- Use `assert` for boolean conditions; reach for `panic` only when you have rich context to dump.

## Examples (compile-verified)

- `examples/19-panic/01-panic-syntax.typ` — safe wrapper that demonstrates the panic call without firing it; the panicking variants are documented inline as comments and verified separately.

## Reference

- Official: https://typst.app/docs/reference/foundations/panic/
