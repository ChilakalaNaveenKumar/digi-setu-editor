# `set-style()` — Set Inherited Style

Sets the current style for the rest of the containing scope (canvas body,
`group`, `scope`).

## Signature

```text
set-style(
  ..style: style,
)
```

## Parameters

- **`..style`** — style key-value pairs. Each one updates a single field of
  the current style.

## Universal keys

```typst
set-style(fill: red, stroke: 2pt + black)
```

## Element-rooted keys

The "root" name of any shape can be used as a key whose value is a sub-
dictionary of styling for that shape:

```typst
set-style(circle: (radius: .3, fill: blue.lighten(60%)))
set-style(rect:   (radius: 25%, fill: yellow.lighten(40%)))
set-style(line:   (mark: (end: ">", scale: 1.2)))
```

Setting `fill`/`stroke` at the top level establishes defaults that the
element-rooted keys then inherit (with `auto` falling back to those
defaults).

## Scoping

`set-style` lives within the *enclosing* scope:

- Canvas body — affects the whole canvas.
- Inside a `group { … }` — only affects that group.
- Inside a `scope { … }` — only affects that scope.

## See also

- [`fill(...)`](./02-fill.md) and [`stroke(...)`](./03-stroke.md) — shorthands.
- [`cetz.styles.resolve`](../internals/styles/01-resolve.md) — exact merge
  algorithm.

## Example

See [`examples/01-set-style/01-set-style.typ`](./examples/01-set-style/01-set-style.typ).
