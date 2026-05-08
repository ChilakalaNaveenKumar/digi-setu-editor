# `util.rotate-anchor()` — Rotate a Cardinal Anchor 90° CW

Returns the anchor rotated 90° clockwise relative to the given one.

```text
#util.rotate-anchor("west")   // → "north"
#util.rotate-anchor("north")  // → "east"
#util.rotate-anchor("east")   // → "south"
#util.rotate-anchor("south")  // → "west"
```

## Signature

```text
rotate-anchor(anchor: str) -> str
```

## Parameters

- **`anchor`** — `str`. The cardinal anchor to rotate. One of `"north"`,
  `"east"`, `"south"`, `"west"`.

## Returns

The same cardinal rotated 90° clockwise.

## Pitfalls

- Like [`opposite-anchor`](./02-opposite-anchor.md), only the four
  cardinals are supported.
- Cycle through all four sides by chaining four calls
  (`"north"` → `"east"` → `"south"` → `"west"` → `"north"`).

## Example

See [`examples/03-rotate-anchor/03-rotate-anchor.typ`](./examples/03-rotate-anchor/03-rotate-anchor.typ).

## Related

- [`02-opposite-anchor.md`](./02-opposite-anchor.md) — opposite (180°)
  rather than 90°.
