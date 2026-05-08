# `assert-version()` — Pin the CeTZ Version

Asserts that the CeTZ version of the current canvas matches the given
version range. Use this in templates / library code to fail loudly when a
caller pulls in an incompatible CeTZ.

## Signature

```text
assert-version(
  min:  version,
  max:  none | version = none,
  hint: string         = "",
)
```

## Parameters

- **`min`** — minimum version (current must be `>= min`).
- **`max`** — first **unsupported** version (current must be `< max`).
- **`hint`** — name of the function/module the assert is called from.
  Surfaced in the error message.

## Pitfalls

- `max` is exclusive. To pin to "0.5.x only", set `min: version(0, 5, 0)`,
  `max: version(0, 6, 0)`.

## Example

See [`examples/01-assert-version/01-assert-version.typ`](./examples/01-assert-version/01-assert-version.typ).
