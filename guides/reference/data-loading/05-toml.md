# `toml()` — Reading and Writing TOML

`toml` parses a TOML document into a Typst dictionary. The companion
`toml.encode(value, pretty: true)` writes a dictionary back to a TOML
string.

## Signature

```text
toml(source: str | bytes)                       -> dictionary
toml.encode(value: dictionary, pretty = true)   -> str
```

TOML documents are **always tables** at the top level — `toml(...)`
therefore always returns a dictionary. To encode a dictionary back to
TOML, the input must also be a dictionary; encoding a bare array or
scalar errors.

## Type conversions (decode)

| TOML                 | Typst                                  |
| -------------------- | -------------------------------------- |
| boolean              | `bool`                                 |
| integer              | `int` (lossless within `±2⁶³−1`; **errors** beyond — TOML mandates this) |
| float                | `float`                                |
| string               | `str`                                  |
| array                | `array`                                |
| inline / std table   | `dictionary`                           |
| date/time            | `datetime`                             |

## Type conversions (encode)

| Typst                                  | TOML                                  |
| -------------------------------------- | ------------------------------------- |
| `none`                                 | omitted                               |
| `bytes`                                | string via `repr` (debug only)        |
| `symbol`                               | string                                |
| `content`                              | table describing the content tree     |
| Other types (`length`, `color`, ...)   | string via `repr` (debug only)        |
| Everything else                        | corresponding TOML value              |

## Tips

- TOML is great for human-edited document configuration: front-matter,
  template parameters, author lists.
- `pretty: false` produces compact TOML (still multi-line, just less
  whitespace).
- `toml.decode(...)` is **deprecated** — pass bytes directly to
  `toml(...)`.
- For binary data prefer [`cbor`](./01-cbor.md) — TOML's `repr`-string
  fallback is debug-only.
