# `anchor.setup()` — Wire Up An Element's Anchors

Builds the anchor map for a shape — combining named anchors, border
anchors, path anchors, and any extra `anchor()` calls inside a `group`.

## Signature

```text
setup(
  callback: function,
  named-anchors: dictionary,
  default: str,
  transform: matrix,
  ...                         // additional internal options
) -> dictionary
```

## Parameters

- **`callback`** — function called by CeTZ to look up an anchor by name.
- **`named-anchors`** — initial map of named anchors.
- **`default`** — name of the default anchor.
- **`transform`** — current transform applied to every resolved anchor.

## Example

End users do not call `anchor.setup` directly — they declare anchors
inside `group(name: ...)` via `anchor("name", coord)` or pass `name:` to
shape calls. See
[`examples/02-setup/02-setup.typ`](./examples/02-setup/02-setup.typ).
