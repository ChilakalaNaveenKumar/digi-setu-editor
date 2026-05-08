# `util.measure()` — Measure Typst Content

Returns the measured width / height of a Typst content fragment as
a 2-tuple `(width, height)` in canvas units. Used by the `content` shape
to size its drawables.

## Signature

```text
measure(ctx: dictionary, cnt: content) -> (float, float)
```

## Parameters

- **`ctx`** — current canvas context.
- **`cnt`** — Typst content.

## Example

See [`examples/16-measure/16-measure.typ`](./examples/16-measure/16-measure.typ).
