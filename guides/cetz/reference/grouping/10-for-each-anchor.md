# `for-each-anchor()` — Iterate Anchors of an Element

Iterates through all named anchors of an element and calls a callback for
each one. The callback returns elements that get added to the canvas.

## Signature

```text
for-each-anchor(
  name:     str,
  callback: function,
  exclude:  array = (),
)
```

## Parameters

- **`name`** — name of the element to iterate.
- **`callback`** — `(anchor-name) => elements`. Inside the callback, `()`
  refers to that anchor's coordinate.
- **`exclude`** — anchor names to skip (e.g. path anchors `start`, `mid`,
  `end` when you only want compass labels).

## Example

See [`examples/10-for-each-anchor/10-for-each-anchor.typ`](./examples/10-for-each-anchor/10-for-each-anchor.typ).
