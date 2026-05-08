# `drawable.content()` — Text/Content Drawable

Constructs a content drawable — a positioned, sized box that wraps a
Typst content value. Used by the `content(...)` shape.

## Signature

```text
content(pos: vector, width: float, height: float, border: array, body: content) -> drawable
```

## Parameters

- **`pos`** — position of the content's centre.
- **`width`**, **`height`** — bounding box size.
- **`border`** — array of border points (used for anchor calculations).
- **`body`** — Typst content to render.

## Example

See [`examples/06-content/06-content.typ`](./examples/06-content/06-content.typ).
