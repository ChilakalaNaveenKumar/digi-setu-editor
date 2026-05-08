# `register-mark()` — Define a Custom Mark

Registers a custom mark (arrowhead, bracket, motif) on the canvas. Once
registered, the symbol can be used wherever a mark name is accepted
(`mark.symbol`, `mark.start`, `mark.end`, `line(..., mark: (end: ":)"))`,
…).

## Signature

```text
register-mark(
  symbol: str,
  body:   function,
  mnemonic:       none | str = none,
  tip:            none | number | coordinate = none,
  base:           none | number | coordinate = none,
  center:         none | number | coordinate = none,
  reverse-tip:    none | number | coordinate = none,
  reverse-base:   none | number | coordinate = none,
  reverse-center: none | number | coordinate = none,
)
```

## Parameters

- **`symbol`** — the mark's name (used as `mark.symbol`).
- **`mnemonic`** — optional short name.
- **`body`** — `(styles) => elements`. Drawing callback. Must register
  anchors named `tip` and `base` (defaulting to `(0, 0)`); optionally
  `center`. CeTZ uses these to orient and position the mark.
- **`tip`**, **`base`**, **`center`** — alternative way to name those
  anchors via numeric/coordinate offsets (`number` → y-component is 0).
- **`reverse-*`** — same set of points, but for when the mark is rendered
  in reverse direction (used for `mark.start`).

## Anchors

The body must register `tip` and `base`. CeTZ automatically computes the
mark direction from `base` → `tip`. If the body provides a `center` anchor
that becomes the mark's centre; otherwise the midpoint of `tip` and `base`
is used.

## Pitfalls

- Forgetting to register `tip` and `base` makes the mark un-orientable.
- Custom marks live for the rest of the canvas scope — re-register them per
  canvas if you want a per-figure custom mark.

## Example

See [`examples/04-register-mark/04-register-mark.typ`](./examples/04-register-mark/04-register-mark.typ).

## Related

- [`mark`](../shapes/05-mark.md) — the user-facing standalone mark shape
- [`internals/mark`](../internals/mark/00-mark-overview.md) — engine
  internals for placing the registered mark on a path
- [`set-style`](./01-set-style.md) — set the default mark for all subsequent shapes
