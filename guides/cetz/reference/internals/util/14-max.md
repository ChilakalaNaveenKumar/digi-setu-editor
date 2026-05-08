# `util.max()` — Max, Skipping `none`

Like `calc.max` but ignores `none` arguments.

## Signature

```text
max(..a: any) -> any
```

## Parameters

- **`..a`** — variadic positional values; `none` entries are skipped. At
  least one non-`none` value must be supplied; an all-`none` invocation
  raises `expected at least one value` from `calc.max` underneath.

## Example

See [`examples/14-max/14-max.typ`](./examples/14-max/14-max.typ).
