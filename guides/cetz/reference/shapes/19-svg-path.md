# `svg-path()` — Build a Path from SVG-like Commands

Creates a path from an array of SVG-like command tuples. Same idea as the SVG
`d="M0 0 L1 0 ..."` attribute, but expressed as a list of Typst tuples.

## Signature

```text
svg-path(
  name:   none | string     = none,
  anchor: none | coordinate = none,
  ..commands-style: any,
)
```

## Supported commands

Uppercase letters use **absolute** coordinates; lowercase use **relative**.

| Tuple | Effect |
| ----- | ------ |
| `("l", coord)` / `("L", coord)` | Line to |
| `("h", number)` / `("H", number)` | Horizontal line |
| `("v", number)` / `("V", number)` | Vertical line |
| `("m", coord)` / `("M", coord)` | Move to (no draw) |
| `("c", c1, c2, end)` | Cubic bezier with two control points |
| `("q", c, end)` | Quadratic bezier |
| `("z",)` | Close the current sub-path |
| `("anchor", name, [coord=(0,0)])` | Register a named anchor on the path |

The anchor named `"default"` serves as the origin for the `anchor:` argument.

## Parameters

- **`name`** — element name.
- **`anchor`** — anchor coordinate to position the path at.
- **`..commands-style`** — path commands and style keys (mixed; styles are
  the named arguments).

## Styling

- **Root:** `svg-path`
- Inherits `fill`, `stroke`.

## Anchors

Path anchors plus any custom anchors registered via the `("anchor", …)`
command.

## Example

See [`examples/19-svg-path/19-svg-path.typ`](./examples/19-svg-path/19-svg-path.typ).

## Related

- [`drawable.path`](../internals/drawable/04-path.md) — the underlying
  multi-subpath drawable structure that `svg-path` populates
- [`path-util.make-subpath`](../internals/path-util/01-make-subpath.md) —
  builds the sub-paths from your command list
- [`compound-path`](./16-compound-path.md) /
  [`merge-path`](./17-merge-path.md) — alternative path-building shapes
