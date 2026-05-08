# `reference-by`

The mode by which references are displayed. Two modes are available:

| Mode | Behaviour |
| ---- | --------- |
| `"line"` | references are displayed as line numbers (formatted by [`reference-number-format`](./53-reference-number-format.md)) |
| `"item"` | references are displayed as items, i.e. by the `tag` for highlights and `content` for annotations |

| Field | Value |
| ----- | ----- |
| Type | `str` |
| Default | `"line"` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Pitfalls

- `"item"` mode requires every referenced highlight to have its `tag:`
  set; annotations need their `content:` set.
- See [`../../tutorial/02-referencing.md`](../../tutorial/02-referencing.md)
  for the three preconditions (numbered figures, `kind: raw`, label on
  the figure).

## Related

- [`52-reference-sep.md`](./52-reference-sep.md),
  [`53-reference-number-format.md`](./53-reference-number-format.md),
  [`44-highlights.md`](./44-highlights.md),
  [`40-annotations.md`](./40-annotations.md),
  [`../../tutorial/02-referencing.md`](../../tutorial/02-referencing.md).
