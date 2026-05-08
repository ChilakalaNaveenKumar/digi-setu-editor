# `relative` (type) — length + ratio combination

A length expressed as the sum of an absolute [length](./14-length.md) and a [ratio](./21-ratio.md):

```typst
25%             // a ratio (which is a relative with zero length component)
1cm             // a length (which is a relative with zero ratio component)
25% + 1cm       // a relative
100% - 2cm      // a relative
```

A bare length or bare ratio is always valid where a `relative` is expected.

## Relative to what?

The percentage component is resolved against the **immediate container**:

| Container             | `width: 50%` resolves to                 |
| --------------------- | ---------------------------------------- |
| Page (no extra container) | 50% of the page's *inner* width (excl. margins) |
| `block(width: 100pt)`  | 50pt                                       |
| `box(width: 100pt)`    | 50pt                                       |

To take 50% of the **full page** including margins, you have a few options:

1. `#set page(margin: 0pt)` (eliminate margins).
2. Multiply the ratio by the known page width: `21cm * 69%`.
3. Use negative `pad` to negate the margins.
4. Place inside `page.background` / `page.foreground` (margins ignored).

## Arithmetic

Relative lengths support multiplication by:

- `int`, `float`
- `ratio`

```typst
((100% + 4pt) * 2)         // 200% + 8pt
```

## Fields

| Field    | Notes                            |
| -------- | -------------------------------- |
| `length`  | The absolute length component.    |
| `ratio`   | The ratio component.              |

```typst
(100% - 50pt).length      // -50pt
(100% - 50pt).ratio       // 100%
```

## Examples (compile-verified)

- `examples/22-relative/01-relative.typ` — relative widths, page vs container resolution, multiplication, `.length`/`.ratio` inspection.

## Reference

https://typst.app/docs/reference/layout/relative/
