# `util.assert-body()` — Validate A Body Argument

Asserts that the supplied value is acceptable as a CeTZ "body" — `none`,
an array of elements, or a function/closure. Used inside CeTZ shapes
that take an inline body block.

## Signature

```text
assert-body(body: any) -> none
```

## Parameters

- **`body`** — value to validate. Panics on invalid input.

## Example

See [`examples/21-assert-body/21-assert-body.typ`](./examples/21-assert-body/21-assert-body.typ).
