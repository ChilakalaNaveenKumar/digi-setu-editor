# `scale` — proportional layout-aware scaling

`quantum-circuit(scale: 60%)` scales every length proportionally and
adjusts the bounding box accordingly. This is **different** from
wrapping the circuit in Typst's built-in `scale(60%, ...)`, which
keeps the original layout slot and visually clips / overflows.

## When to use which

| You want | Use |
| -------- | --- |
| Smaller circuit *and* smaller bounding box | `quantum-circuit(scale: 60%, ...)` |
| Scale the visual but keep the original layout slot (e.g. for layout debugging) | `scale(60%, quantum-circuit(...))` |

## Example

```typst
#quantum-circuit(
  scale: 60%,
  1, $H$, ctrl(1), $H$, 1, [\ ],
  1, 1, targ(), 2
)
```

See [`examples/03-scale/03-scale.typ`](examples/03-scale/03-scale.typ).

## Pitfalls

- `scale: 60%` shrinks gate text too. For very small scales, set
  `font-size:` higher to keep things readable.
- `scale: 200%` produces a circuit twice as large *and* twice the
  width / height. If you only want to tighten layout, prefer
  `row-spacing` / `column-spacing`.
- Negative or zero scales are not supported.

## Related

- Per-cell tuning: [tutorial 9](../../tutorial/09-fine-tuning.md)
- Spacing options: [`01-spacing.md`](01-spacing.md)
