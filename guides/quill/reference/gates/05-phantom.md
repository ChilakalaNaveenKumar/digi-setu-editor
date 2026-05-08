# `phantom()` — invisible space-reserving gate

Reserves cell space without drawing anything. Useful for aligning
circuits side-by-side or carving out room for an `annotate` callback.

## Signature

```typst
phantom(
  content: content = none,
  width:   length  = 0pt,
  height:  length  = 0pt,
  x, y,
)
```

- If `content` is non-`none`, the phantom takes the same size that
  `gate(content)` would have (with default padding).
- If `content` is `none`, `width` and `height` create a **bare**
  rectangle of the requested size (no padding added).

## Examples

```typst
// Reserve space for a Hadamard-sized gate.
#quantum-circuit(1, phantom($H$), 1)

// Reserve a fixed 1cm-wide cell.
#quantum-circuit(1, phantom(width: 1cm), 1)
```

See [`examples/05-phantom/05-phantom.typ`](examples/05-phantom/05-phantom.typ).

## Why use `phantom`?

- Aligning two circuits (e.g. before / after) so corresponding columns
  share an x-coordinate.
- Reserving room for an annotation that the circuit's bounding box
  would otherwise clip.
- Forcing a specific column width without inserting a real gate.

## Pitfalls

- `phantom(content: $H$, width: 1cm)` ignores `width` because `content`
  is given. Pass either `content` **or** `width`+`height`, never both.
- Phantoms still **occupy a cell** — they advance the column counter
  unless placed manually with `x:` / `y:`.

## Related

- Space-only items: lengths between gates ([tutorial 9](../../tutorial/09-fine-tuning.md))
- Manual placement: [tutorial 7](../../tutorial/07-gate-placement.md)
