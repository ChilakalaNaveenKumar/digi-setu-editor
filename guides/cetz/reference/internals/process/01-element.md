# `process.element()` — Run a Single Element

Runs a single element function against a context — calling the element's
`render` callback, applying any post-transforms, accumulating the result
into the context's drawable list, and updating its bounding box.

## Signature

```text
element(ctx: dictionary, element-func: function) -> dictionary
```

## Parameters

- **`ctx`** — current canvas context.
- **`element-func`** — a CeTZ element (the value returned by, say,
  `circle((0, 0))` before it is finalized).

## Example

This function is invoked by `cetz.canvas` and is rarely used directly.
See [`examples/01-element/01-element.typ`](./examples/01-element/01-element.typ).
