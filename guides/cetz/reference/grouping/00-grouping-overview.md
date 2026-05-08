# Grouping — Overview

Helpers for **scoping**, **introspection**, and **layering** of drawings.

| Function | Purpose | Page |
| -------- | ------- | ---- |
| `hide(body)` | Hide elements (still affect layout depending on `bounds`). | [`01-hide.md`](./01-hide.md) |
| `floating(body)` | Draw without affecting bounding boxes. | [`02-floating.md`](./02-floating.md) |
| `intersections(name, ..elements)` | Compute intersection points → numbered anchors. | [`03-intersections.md`](./03-intersections.md) |
| `group(body, name, anchor, ..style)` | Scope transforms / styles + name a sub-drawing. | [`04-group.md`](./04-group.md) |
| `scope(body)` | Like `group` but doesn't expose itself as a named element. | [`05-scope.md`](./05-scope.md) |
| `anchor(name, position)` | Register a custom anchor inside a group. | [`06-anchor.md`](./06-anchor.md) |
| `copy-anchors(element, filter)` | Copy anchors from one element into the surrounding group. | [`07-copy-anchors.md`](./07-copy-anchors.md) |
| `set-ctx(callback)` | Mutate the canvas `ctx` (transform matrix, shared data, …). | [`08-set-ctx.md`](./08-set-ctx.md) |
| `get-ctx(callback)` | Read the canvas `ctx` and return elements based on it. | [`09-get-ctx.md`](./09-get-ctx.md) |
| `for-each-anchor(name, callback)` | Iterate every named anchor on an element. | [`10-for-each-anchor.md`](./10-for-each-anchor.md) |
| `on-layer(layer, body)` | Place elements on a specific draw layer. | [`11-on-layer.md`](./11-on-layer.md) |

These functions don't draw geometry directly — they manipulate scope, the
context, and the draw-order.
