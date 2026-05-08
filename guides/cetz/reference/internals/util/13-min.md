# `util.min()` — Min, Skipping `none`

Like `calc.min` but ignores `none` arguments — useful when an optional
value might be missing.

## Signature

```text
min(..a: any) -> any
```

## Parameters

- **`..a`** — variadic positional values; `none` entries are skipped. At
  least one non-`none` value must be supplied; an all-`none` invocation
  raises `expected at least one value` from `calc.min` underneath.

## Example

See [`examples/13-min/13-min.typ`](./examples/13-min/13-min.typ).
