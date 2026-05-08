# `util.opposite-anchor()` — Mirror a Cardinal Anchor

Returns the anchor on the opposite side of the given one.

```text
#util.opposite-anchor("west")   // → "east"
#util.opposite-anchor("north")  // → "south"
```

## Signature

```text
opposite-anchor(anchor: str) -> str
```

## Parameters

- **`anchor`** — `str`. The input anchor. One of the four cardinal
  directions (`"north"`, `"east"`, `"south"`, `"west"`).

## Returns

The mirrored cardinal: `"north" ↔ "south"`, `"east" ↔ "west"`.

## Pitfalls

- The function only knows the four cardinals; passing a compound or
  arbitrary anchor name (e.g. `"north-east"` or a port-anchor) is undefined.

## Example

See [`examples/02-opposite-anchor/02-opposite-anchor.typ`](./examples/02-opposite-anchor/02-opposite-anchor.typ).

## Related

- [`03-rotate-anchor.md`](./03-rotate-anchor.md) — rotate by 90° instead
  of mirroring.
- [`../wire/02-stub.md`](../wire/02-stub.md) — `stub` takes a side
  argument that is exactly one of these cardinals.
