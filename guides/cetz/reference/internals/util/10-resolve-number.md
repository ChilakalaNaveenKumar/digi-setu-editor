# `util.resolve-number()` — Coerce A Value Into A Float

Resolves a number-like value (length, ratio, integer, float, decimal, or
parseable string) into a CeTZ-canvas float, using the canvas length unit
where needed.

## Signature

```text
resolve-number(ctx: dictionary, num: any) -> float
```

## Parameters

- **`ctx`** — current canvas context.
- **`num`** — value to resolve.

## Example

See [`examples/10-resolve-number/10-resolve-number.typ`](./examples/10-resolve-number/10-resolve-number.typ).
