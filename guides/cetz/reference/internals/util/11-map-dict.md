# `util.map-dict()` — Map Over Dictionary Values

Returns a new dictionary with `fn(key, value)` applied to each entry.

## Signature

```text
map-dict(d: dictionary, fn: function) -> dictionary
```

## Parameters

- **`d`** — input dictionary.
- **`fn`** — `(key, value) -> new-value` callback.

## Example

See [`examples/11-map-dict/11-map-dict.typ`](./examples/11-map-dict/11-map-dict.typ).
