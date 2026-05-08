# `anchor()` — Register a Named Anchor

Creates a new anchor for the current group. The anchor is then accessible
inside the group by its name, and outside the group via
`"<group>.<anchor>"`.

## Signature

```text
anchor(
  name:     str,
  position: coordinate,
)
```

## Parameters

- **`name`** — the anchor name. Use `"default"` to override the group's
  default anchor (otherwise `center`).
- **`position`** — coordinate of the anchor.

## Pitfalls

- `anchor` *requires* a surrounding [`group`](./04-group.md) (or the canvas
  root scope). Calling it outside a group panics.
- Registering an anchor named `"default"` changes how `(rel: ...)` and
  `<group>` (without `.anchor`) resolve.

## Example

See [`examples/06-anchor/06-anchor.typ`](./examples/06-anchor/06-anchor.typ).

## Related

- [`copy-anchors`](./07-copy-anchors.md) — bulk-copy anchors from a child
  element into the current group
- [`for-each-anchor`](./10-for-each-anchor.md) — iterate every anchor on
  an element
- [`internals/anchor`](../internals/anchor/00-anchor-overview.md) — the
  internal anchor resolver (`border`, `setup`)
- Tutorial: [Anchors](../../tutorial/04-anchors.md)
