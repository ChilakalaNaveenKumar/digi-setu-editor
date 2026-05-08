# `group()` — Scoped, Named Sub-Drawing

Groups elements together in a scope. State changes (transforms, styles)
inside the group only affect the group's own children. The group itself is a
named element — you can refer to its anchors and place other elements
relative to it.

## Signature

```text
group(
  body:    elements | function,
  name:    none | str = none,
  anchor:  none | str = none,
  ..style: style,
)
```

## Parameters

- **`body`** — elements to group, or a function `(ctx) => elements`.
- **`name`** — element name; allows `"<name>.<anchor>"` references later.
- **`anchor`** — anchor to position the group's `default` at. The group is
  translated so that the named anchor coincides with the original `default`
  position.
- **`padding`** *(style)* — extra padding around the group's bounding box.
  `none`, a number (uniform), an array (CSS shorthand), or a Typst pad-style
  dictionary.

## Anchors

Border + path anchors of the axis-aligned bounding box of the children.

Custom anchors can be added inside the group with [`anchor`](./06-anchor.md);
the default anchor (`center`) can be overridden by registering an anchor
named `default`.

Named children of the group are reachable from outside via dotted notation:

```typst
group(name: "a", { circle((), name: "b") })
circle("a.b.south", radius: 0.2)
```

## Pitfalls

- `set-style` and transforms inside the group are scoped to the group.
- The group's bounding box is computed from its children — invisible
  ([`hide`](./01-hide.md)) elements influence it depending on `bounds`.

## Example

See [`examples/04-group/04-group.typ`](./examples/04-group/04-group.typ).
