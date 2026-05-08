# `drawable.filter-tagged()` — Drop Drawables With Matching Tags

Returns `drawables` with every entry that carries at least one of the
listed tags removed. (Note that the function *removes* matching items —
the name describes the predicate it filters by.)

## Signature

```text
filter-tagged(drawables: drawable | array, ..tags: str) -> drawable | array | none
```

## Parameters

- **`drawables`** — list of drawables.
- **`..tags`** — variadic tag names.

## Example

See [`examples/03-filter-tagged/03-filter-tagged.typ`](./examples/03-filter-tagged/03-filter-tagged.typ).
