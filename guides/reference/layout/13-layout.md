# `layout(fn)` — access the outer container's dimensions

Calls `fn(size)` where `size` is `(width: length, height: length)` of the **outer container** — the parent box, or the page minus margins if there's no enclosing container.

The function is implicitly run with `context`, so you can call `measure()`, `counter.get()`, etc., directly inside.

## Parameters

| Param  | Type      | Default  | Notes                                                       |
| ------ | --------- | -------- | ----------------------------------------------------------- |
| `func` | function  | required | `(size) → content`. Called once per occurrence of the result. |

## Common patterns

| Goal                                              | Recipe                                                |
| ------------------------------------------------- | ----------------------------------------------------- |
| Measure content sized to the current width        | `layout(size => measure(width: size.width, body))`     |
| Get **remaining** page height (not the full page) | Wrap in `block(height: 1fr, layout(...))`              |
| Resolve a ratio (e.g. `50%`) to an absolute length | `layout(size => 50% * size.width)`                     |

## Restrictions

- `layout` forces its content into a **block**-level container — pagebreaks and page-relative placement don't work inside it.
- If the enclosing dimension is `auto`, the corresponding `width` / `height` will be **infinite** (`length` with infinite value), since there's no fixed bound.

## Examples (compile-verified)

- `examples/13-layout/01-layout.typ` — measure with current width, remaining-height trick via `block(height: 1fr)`, ratio resolution.

## Reference

https://typst.app/docs/reference/layout/layout/
