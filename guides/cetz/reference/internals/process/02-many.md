# `process.many()` — Run Multiple Elements

Runs an array (or comma-separated content) of elements through
`process.element` in order. This is what `cetz.canvas` calls on the body
you pass it.

## Signature

```text
many(ctx: dictionary, body: content | array) -> dictionary
```

## Parameters

- **`ctx`** — current canvas context.
- **`body`** — the elements to run.

## Example

See [`examples/02-many/02-many.typ`](./examples/02-many/02-many.typ).
