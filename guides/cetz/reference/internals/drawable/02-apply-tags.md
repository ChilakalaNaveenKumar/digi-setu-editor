# `drawable.apply-tags()` — Tag Drawables

Attaches a set of tags to each drawable. Tags are used for layered
rendering, picking, and filtering with `filter-tagged`.

## Signature

```text
apply-tags(drawables: drawable | array, ..tags: str) -> drawable | array
```

## Parameters

- **`drawables`** — a single drawable, or an array of drawables. The
  function returns the same shape it was given.
- **`..tags`** — variadic tag names.

## Example

See [`examples/02-apply-tags/02-apply-tags.typ`](./examples/02-apply-tags/02-apply-tags.typ).
