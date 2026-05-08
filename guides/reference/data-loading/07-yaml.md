# `yaml()` — Reading and Writing YAML

`yaml` parses a YAML document into Typst values. The companion
`yaml.encode(value)` produces a YAML string.

## Signature

```text
yaml(source: str | bytes)        -> any
yaml.encode(value: any)          -> str
```

## Type conversions (decode)

| YAML                                  | Typst                          |
| ------------------------------------- | ------------------------------ |
| null (`null`, `~`, empty)             | `none`                         |
| boolean                               | `bool`                         |
| integer (whole)                       | `int` (lossy past `±2⁶³−1`)    |
| number (non-whole)                    | `float`                        |
| string                                | `str`                          |
| sequence                              | `array`                        |
| mapping                               | `dictionary`                   |

Custom YAML tags are **ignored**; the underlying value still loads.

## Type conversions (encode)

| Typst                                  | YAML                              |
| -------------------------------------- | --------------------------------- |
| `bytes`                                | string via `repr` (debug only)    |
| `symbol`                               | string                            |
| `content`                              | mapping describing the content tree |
| Other types (`length`, `color`, ...)   | string via `repr` (debug only)    |
| Everything else                        | corresponding YAML value          |

## Tips

- YAML is a great fit for hand-edited author lists, bibliographies, and
  per-chapter overrides — the syntax tolerates short hand-written entries
  better than JSON.
- `yaml.decode(...)` is **deprecated** — pass bytes directly to
  `yaml(...)`.
- For binary data prefer [`cbor`](./01-cbor.md).
