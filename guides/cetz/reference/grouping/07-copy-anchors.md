# `copy-anchors()` — Lift Anchors Into the Surrounding Group

Copies multiple anchors from a named child element into the **current**
group, making them appear as if they were registered there with
[`anchor`](./06-anchor.md). Panics when used outside of a `group`.

## Signature

```text
copy-anchors(
  element: str,
  filter:  auto | array = auto,
)
```

## Parameters

- **`element`** — name of the element to copy anchors from.
- **`filter`** — `auto` copies all anchors. Pass an array of anchor names to
  cherry-pick (only those that exist on the element are copied).

## Pitfalls

- Useful when wrapping a sub-drawing in a `group(name: …)` and you want
  outer code to use the inner element's anchors *directly* (`group.x` instead
  of `group.inner.x`).

## Example

See [`examples/07-copy-anchors/07-copy-anchors.typ`](./examples/07-copy-anchors/07-copy-anchors.typ).
