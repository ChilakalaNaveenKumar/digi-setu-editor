# `anchor` — Anchor Bookkeeping

`cetz.anchor` (in the package source: `src/anchor.typ`) keeps track of the
named anchors a shape exposes and the rules for resolving border / path
anchors against a shape's drawables.

> **Internal module — not re-exported.** `cetz.anchor.*` is *not*
> reachable via `cetz.<x>` from outside the package. The functions are
> documented here for completeness; in user code, anchors are driven
> through the `anchor()` element from `cetz.draw` and the `name:`
> arguments on shapes.

## Functions

| File | Function |
| --- | --- |
| [`01-border.md`](./01-border.md) | `border()` |
| [`02-setup.md`](./02-setup.md) | `setup()` |

## Related

- Tutorial: [Anchors](../../../tutorial/04-anchors.md) — the user model
- [`anchor`](../../grouping/06-anchor.md) — register an anchor on a group
- [`copy-anchors`](../../grouping/07-copy-anchors.md) — bulk-copy anchors
- [`for-each-anchor`](../../grouping/10-for-each-anchor.md) — iterate them
