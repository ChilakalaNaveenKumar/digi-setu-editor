# `baseline` — vertical anchor

`baseline:` controls where the circuit sits **vertically** relative
to surrounding text — useful when embedding a circuit inline next to
an equation.

## Accepted forms

| Form | Meaning |
| ---- | ------- |
| `length` (e.g. `0pt`, `-3pt`) | Offsets the circuit's baseline by that length. Default is `0pt`. |
| `content` / `str` (e.g. `"="`, `[$=$]`) | Aligns the circuit's vertical centre with the centre of the given content. |

## Manual offset

```typst
Hello #quantum-circuit(baseline: -2pt, 1, $H$, 1) world.
```

```typst
Eq: #quantum-circuit(baseline: -8pt, 1, $H$, ctrl(1), [\ ], 1, targ()) end.
```

See [`examples/04-baseline/04-baseline.typ`](examples/04-baseline/04-baseline.typ).

## Pitfalls

- **Quill 0.7.2 bug:** using `baseline: "="` (or any string / content)
  inside a math equation (`$ ... $`) currently fails with
  `error: unknown variable: height`. Until upstream is fixed, prefer
  a numeric `baseline: -8pt` (or similar) for inline-math alignment.
- Offsets are independent of `gate-padding` — fine-tune visually.

## Related

- Inline math: core Typst `equation` reference (search `search_typst_docs`).
