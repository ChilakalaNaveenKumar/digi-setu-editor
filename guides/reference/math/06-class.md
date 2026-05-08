# `math.class(class, body)` — force a math class on content

A symbol's **math class** controls the spacing around it and how attachments default (scripts vs limits). Use `class()` to override the class of an arbitrary symbol or expression.

## Available classes

| Class           | Behaviour                                                  | Examples         |
| --------------- | ---------------------------------------------------------- | ---------------- |
| `"normal"`       | Default for variables/letters                              | `x`, `A`         |
| `"punctuation"`  | Comma-like spacing                                         | `,`              |
| `"opening"`      | Opening delimiter — tight on the right                     | `(`, `[`, `{`   |
| `"closing"`      | Closing delimiter — tight on the left                      | `)`, `]`, `}`   |
| `"fence"`        | Symmetric delimiter                                        | `|`              |
| `"large"`        | Big operator — gets **limits** in block mode by default     | `sum`, `product`, `integral` |
| `"relation"`     | Relation — generous spacing on both sides                  | `=`, `<`, `in`   |
| `"unary"`        | Unary operator — tight on the right                        | `not`            |
| `"binary"`       | Binary operator — generous spacing on both sides           | `times`, `plus.minus` |
| `"vary"`         | Sometimes unary, sometimes binary (context-dependent)      | `+`, `-`         |

## Use cases

- Reclassify a symbol from your domain (e.g., a music symbol) as a relation so it sits between operands with proper spacing.
- Make a custom multi-letter identifier behave as a *big operator* (gets `limits` in block mode).
- Promote an expression to *opening*/*closing* so `lr()` matches it as a delimiter.

To override **just** the script/limit positioning (without touching spacing), reach for [`scripts()`/`limits()`](./02-attach.md) instead.

## Examples (compile-verified)

- `examples/06-class/01-class.typ` — heart as relation, custom multi-letter `"large"` operator, custom `"opening"` delimiter.

## Reference

https://typst.app/docs/reference/math/class/
