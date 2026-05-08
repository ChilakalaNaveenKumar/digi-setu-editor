# `colbreak(weak: false)` — force a column break

Forces the next content into the next column. Behaves like a page break in single-column layouts or in the last column on a page.

## Parameters

| Param   | Type | Default  | Notes                                                       |
| ------- | ---- | -------- | ----------------------------------------------------------- |
| `weak`  | bool  | `false`   | Skip the break if the current column is already empty.      |

## Examples (compile-verified)

- `examples/06-colbreak/01-colbreak.typ` — split content across columns, weak break behavior.

## Related

- [`columns`](./07-columns.md) — set up multiple columns in a region.
- [`page(columns: ...)`](./18-page.md) — page-level columns.

## Reference

https://typst.app/docs/reference/layout/colbreak/
