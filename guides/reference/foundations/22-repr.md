# `repr` — debug-style string representation

`repr(value) -> str` returns a string with the debugger-style representation of any value. Most values inserted into content already display in this form (rendered in monospace with syntax highlighting). The exceptions — values that print their **own** visible form, not their repr — are:

- `none` (invisible)
- integers and floats (decimal output)
- strings (raw text, no surrounding quotes)
- content (the rendered content itself)
- functions (function name when known)

For everything else (arrays, dictionaries, lengths, colors, datetimes, etc.) inserting the value into content is functionally equivalent to inserting `repr(value)`.

## Common debugging shape

```typst
#let dbg(label, value) = [
  *#label*: #raw(repr(value)) \
]

#dbg("config", (port: 8080, retries: 3))
#dbg("len",    2pt / 3)
```

`raw(...)` keeps the repr verbatim in monospace; useful for long values.

## For debugging only

The output of `repr` is **not stable** and is **not** the inverse of `eval`:

- Lengths are rounded for display: `repr(2pt / 3)` shows a finite decimal, but the underlying value is more precise.
- Unnamed function reprs omit body and parameter list.
- New Typst versions can reformat repr output without notice.

Don't use repr as a serialization format. For interchange use a real format (`json.encode`, `yaml.encode`, `cbor.encode`).

## Pitfalls

- **`repr(content)` may surprise you** — content reprs are deeply nested and verbose for anything beyond trivial markup. Stick to scalar / collection types when debugging.
- **Inserting a value to "see what it is" only works for non-exception types.** If you write `#none` and see nothing, that's correct — switch to `#repr(none)` to confirm.
- **Diffing two values via repr is unreliable.** Same repr ≠ same value (the docs explicitly say so).

## Examples (compile-verified)

- `examples/22-repr/01-repr-of-various.typ` — `repr` of `none`, string, array, content, length math, dictionary, and an unnamed function. Compares the repr form to the direct-insert form for each.

## Reference

- Official: https://typst.app/docs/reference/foundations/repr/
