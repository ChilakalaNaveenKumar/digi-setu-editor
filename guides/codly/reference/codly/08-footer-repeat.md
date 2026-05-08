# `footer-repeat`

Whether to repeat the footer on each page. See
[`header-repeat`](./04-header-repeat.md) for more information.

| Field | Value |
| ----- | ----- |
| Type | `bool` |
| Default | `false` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Pitfalls

- Same three preconditions as `header-repeat`: `footer` must be set,
  `breakable: true`, and the block must actually break across pages.

## Related

- [`07-footer.md`](./07-footer.md), [`04-header-repeat.md`](./04-header-repeat.md).
