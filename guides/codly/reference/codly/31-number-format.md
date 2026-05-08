# `number-format`

The format of the line numbers — a function that takes the line `number`
(int) and returns content. If set to `none`, **disables line numbers**
entirely.

| Field | Value |
| ----- | ----- |
| Type | `function` or `none` |
| Default | `numbering.with("1")` (often shown in code as `(number) => [ #number ]`) |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(number-format: numbering.with("I."))
```py
print('Hello, world!')
print('Goodbye, world!')
```
```

Renders line numbers as `I.`, `II.`, `III.`, …

See [`examples/31-number-format/31-number-format.typ`](./examples/31-number-format/31-number-format.typ).

## Pitfalls

- `numbering.with("1")` produces decimal; `"I"` Roman; `"a"` lowercase
  letters; `"①"` circled digits, etc. — see Typst's `numbering` docs.
- Disable line numbers entirely with `number-format: none`.

## Related

- [`32-number-align.md`](./32-number-align.md),
  [`33-number-placement.md`](./33-number-placement.md),
  [`53-reference-number-format.md`](./53-reference-number-format.md).
