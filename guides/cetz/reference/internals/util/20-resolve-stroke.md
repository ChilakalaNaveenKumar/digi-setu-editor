# `util.resolve-stroke()` — Coerce Into A Typst Stroke

Coerces the various accepted "stroke" forms — number (paint thickness),
length, color, dictionary, or `stroke` value — into a Typst `stroke`.

## Signature

```text
resolve-stroke(stroke: any) -> stroke
```

## Parameters

- **`stroke`** — input stroke spec.

## Example

See [`examples/20-resolve-stroke/20-resolve-stroke.typ`](./examples/20-resolve-stroke/20-resolve-stroke.typ).
