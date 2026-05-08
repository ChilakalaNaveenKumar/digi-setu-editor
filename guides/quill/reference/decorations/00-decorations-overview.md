# Decorations — overview

Decorations are circuit children that **don't add a gate cell**. They
attach labels (`lstick`, `rstick`, `midstick`, `nwire`), change wire
style (`setwire`), or draw overlays (`gategroup`, `slice`, `annotate`).

| Function | Purpose | Page |
| -------- | ------- | ---- |
| [`lstick`](01-lstick.md) | Label / brace at the **start** of a wire. | 01 |
| [`rstick`](02-rstick.md) | Label / brace at the **end** of a wire. | 02 |
| [`midstick`](03-midstick.md) | Plain text on the wire (e.g. `…`). | 03 |
| [`nwire`](04-nwire.md) | Wire-bundle marker (slash + label). | 04 |
| [`setwire`](05-setwire.md) | Switch wire style (count, stroke, distance). | 05 |
| [`gategroup`](06-gategroup.md) | Labelled rectangle around a contiguous block. | 06 |
| [`slice`](07-slice.md) | Vertical line marking a phase boundary. | 07 |
| [`annotate`](08-annotate.md) | Custom callback receiving cell coordinates. | 08 |

## Family resemblances

- **`lstick` / `rstick`** share the same shape: `body, n, brace, pad,
  label, x, y`. Only the side and default brace differ.
- **`gategroup` / `slice`** both accept `wires`/`steps`,
  `x`/`y`/`right`/`bottom`, `z: above|below`, and `label`.
- **`setwire` / `annotate`** are *cell-less* — they take no column slot
  and only modify state / draw overlays.

## Z-order

`slice`, `gategroup`, and `annotate` accept `z: "above" | "below"` to
control draw order relative to the gates. Default is `"below"`.
