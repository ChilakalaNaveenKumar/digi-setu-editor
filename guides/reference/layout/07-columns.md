# `columns(count, gutter: 4% + 0pt, body)` — split a region into columns

Splits a container into equally sized columns. Heights are not balanced — columns just take the available height of their container.

## Parameters

| Param    | Type      | Default        | Notes                                          |
| -------- | --------- | -------------- | ---------------------------------------------- |
| `count`  | int        | `2`             | Number of columns.                             |
| `gutter` | relative   | `4% + 0pt`     | Space between columns.                         |
| `body`   | content    | required        | The content to lay out.                         |

Use [`colbreak()`](./06-colbreak.md) to explicitly continue in the next column.

## Local vs page-level columns

| Approach                       | Use when                                                  |
| ------------------------------ | --------------------------------------------------------- |
| `#columns(2)[...]`              | Need columns only for a region; container is fine.         |
| `#set page(columns: 2)`         | Whole document or pages; pagebreaks/footnotes/line numbers must keep working. |

`#columns(...)` wraps content in a layout container — pagebreaks and other page-level features don't reach inside.

## Breaking out of columns

To create a single-column span (paper title, full-width figure) inside a multi-column page:

```typst
#set page(columns: 2)

#place(
  top + center,
  scope: "parent",      // span across columns
  float: true,
  text(1.4em, weight: "bold")[My document],
)
```

`scope: "parent"` requires `float: true`.

## Examples (compile-verified)

- `examples/07-columns/01-columns.typ` — local 2-column block, page-level columns with parent-scoped title.

## Reference

https://typst.app/docs/reference/layout/columns/
