# `fraction` (type) — the `fr` unit

The `fr` (fraction) unit defines how **remaining space** in a layout is distributed among elements. Each fractionally sized element gets space proportional to its fraction divided by the sum of all fractions in the same context.

```typst
Left #h(1fr) Middle #h(2fr) Right
// Middle is twice as far from "Right" as it is from "Left".
```

> **Note:** This `fraction` is the **layout `fr` unit**, distinct from `math.frac` (the math fraction `a/b`).

## Where it appears

| Context                          | Example                                  | Effect                              |
| -------------------------------- | ---------------------------------------- | ----------------------------------- |
| Horizontal spacing in paragraphs | `Left #h(1fr) Right`                      | Push to opposite edges               |
| Vertical spacing in a flow       | `#v(1fr)`                                 | Fill leftover vertical space         |
| Block height                     | `#block(height: 1fr, ...)`                | Fill remaining page height           |
| Grid / table columns             | `columns: (1fr, 2fr, auto)`               | Weighted column widths               |
| Box width (in paragraph only)    | `#box(width: 1fr, line(length: 100%))`    | Flexible inline width               |

## Restrictions

- Only **widths** can be fractional inside a paragraph (`box(width: 1fr)` works; height does not).
- Outside paragraphs, both width and height (where applicable) accept fractions.
- Fractional spacing collapses to zero if there's nothing else to fill against.

## Examples (compile-verified)

- `examples/09-fraction/01-fraction.typ` — `h(1fr)` paragraph spacing, mixed `(auto, 1fr, 2fr)` grid columns, `block(height: 1fr)` to fill remaining page.

## Reference

https://typst.app/docs/reference/layout/fraction/
