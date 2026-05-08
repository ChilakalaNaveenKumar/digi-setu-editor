# Util — Overview

Small string / anchor helpers and a predefined colour palette. Available
as `util.<name>` after `import circuiteria: *` (or
`circuiteria.util.<name>` from outside).

| Function | Purpose | Page |
| -------- | ------- | ---- |
| `lpad(string, len)` | Pad a string on the left with `0`s up to `len` chars. | [`01-lpad.md`](./01-lpad.md) |
| `opposite-anchor(anchor)` | Return the opposite cardinal anchor (`"east"` ↔ `"west"`, `"north"` ↔ `"south"`). | [`02-opposite-anchor.md`](./02-opposite-anchor.md) |
| `rotate-anchor(anchor)` | Return the cardinal anchor rotated 90° clockwise. | [`03-rotate-anchor.md`](./03-rotate-anchor.md) |

Variables:

| Name | Purpose | Page |
| ---- | ------- | ---- |
| `colors` | Predefined colour palette (`orange`, `yellow`, `green`, `pink`, `purple`, `blue`). | [`04-colors.md`](./04-colors.md) |

Most of these helpers exist to make port labelling, mirrored-side
placement, and consistent block colouring easier without re-importing
CeTZ utilities by hand.
