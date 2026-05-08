# `move(dx: 0pt, dy: 0pt, body)` — visual offset without affecting layout

Shifts content visually. Containers stay sized as if the content were not moved — useful for drop shadows, micro-typography tweaks, and overlays.

## Parameters

| Param | Type      | Default      | Notes                                                       |
| ----- | --------- | ------------ | ----------------------------------------------------------- |
| `dx`  | relative   | `0% + 0pt`    | Horizontal displacement (positive = right).                  |
| `dy`  | relative   | `0% + 0pt`    | Vertical displacement (positive = down).                     |
| `body` | content   | required     | The content to move.                                          |

## Common patterns

| Goal              | Recipe                                                          |
| ----------------- | --------------------------------------------------------------- |
| Drop shadow       | `rect(fill: gray, move(dx: 4pt, dy: 6pt, rect(...)))`            |
| Micro-typography  | `move(dy: -3pt)[some superscript-like text]`                     |
| Manual overlay    | `box[#image(...) #move(dx: -100%, ...)[label]]`                   |

## Accessibility

The movement is purely visual. **Assistive Technology reads the content in source order** regardless of where it ends up on the page. If you need to hide content from AT entirely (PDF), use `pdf.artifact`.

## Related

- [`place`](./20-place.md) — absolute positioning *with* alignment, container-relative.
- [`rotate`](./24-rotate.md), [`scale`](./25-scale.md), [`skew`](./26-skew.md) — other transforms.

## Examples (compile-verified)

- `examples/16-move/01-move.typ` — drop shadow, in-line micro-typography shift, negative offsets.

## Reference

https://typst.app/docs/reference/layout/move/
