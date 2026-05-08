# `scope()` — Scoped State Without a Named Element

Like [`group`](./04-group.md), `scope` makes state changes (transforms,
styles) only affect the elements inside its body. Unlike `group`, `scope`:

- does **not** create a named element of its own, and
- **leaks** the body's elements (and their anchors) into the surrounding
  scope.

## Signature

```text
scope(
  body: elements | function,
)
```

## Parameters

- **`body`** — elements to scope (or a function `(ctx) => elements`).

## When to choose `scope` vs `group`

| Goal | Use |
| ---- | --- |
| Scoped style/transform, *without* needing the bundle as one named element | `scope` |
| Scoped state *and* a named bundle for downstream anchor references | `group` |

## Example

See [`examples/05-scope/05-scope.typ`](./examples/05-scope/05-scope.typ).
