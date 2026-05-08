# `on-layer()` — Place on a Specific Draw Layer

Places elements on a specific layer. Layers determine the position of an
element in the draw queue: lower layers are drawn first, so higher layers
appear in front of lower ones.

## Signature

```text
on-layer(
  layer: float | int,
  body:  elements | function,
)
```

## Parameters

- **`layer`** — the layer to place the elements on. The default layer
  (without `on-layer`) is `0`. Negative layers go behind, positive in front.
- **`body`** — elements to draw, or `(ctx) => elements`.

## Pitfalls

- An element's bounding box still affects canvas size on every layer.
- Useful for drawing a background highlight *behind* text whose layout
  position is needed for the highlight rect (compute the rect after the
  text exists, then place it on a lower layer).

## Example

See [`examples/11-on-layer/11-on-layer.typ`](./examples/11-on-layer/11-on-layer.typ).
