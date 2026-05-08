# `translate()` — Translate the Coordinate System

Translates the transformation matrix by the given vector or named offsets.

## Signature

```text
translate(
  ..args: vector | float | length,
  pre:    bool = false,
)
```

## Parameters

- **`..args`** — either a single positional vector, or named arguments
  `x:`, `y:`, `z:`. Builds a translation matrix and multiplies it with the
  current transform.
- **`pre`** — controls multiplication order:
  - `false` (default): `World = World * Translate` — translation in the
    current local frame.
  - `true`: `World = Translate * World` — pre-multiply, translation in the
    world frame.

## Example

See [`examples/04-translate/04-translate.typ`](./examples/04-translate/04-translate.typ).
