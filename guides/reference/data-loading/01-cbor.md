# `cbor()` — Reading and Writing CBOR

`cbor` reads structured data from a CBOR file (or raw bytes) and decodes
it into Typst values. The companion `cbor.encode(value)` produces CBOR
`bytes` from any value.

## Signature

```text
cbor(source: str | bytes) -> any
cbor.encode(value: any)   -> bytes
```

CBOR (Concise Binary Object Representation) is a compact, JSON-like
binary format. It's the recommended interchange when you need
binary-clean encoding, especially when shipping data to a Typst
[`plugin`](../foundations/16-plugin.md).

## Type conversions (decode)

CBOR types map to Typst values as expected: maps → dictionaries, arrays →
arrays, ints → `int` (with the same `±2⁶³−1` caveat as JSON/YAML), floats
→ `float`, text strings → `str`, booleans/null as expected.

## Type conversions (encode)

`cbor.encode` accepts anything Typst can hold. Most types round-trip
losslessly. A few don't:

| Source value                          | CBOR value                                  |
| ------------------------------------- | ------------------------------------------- |
| `symbol`                              | text                                         |
| `content`                             | a map describing the content tree            |
| Other types (`length`, `color`, ...)  | text via `repr` (debug only)                 |

CBOR **tags are not supported** — both for decoding and encoding. Files
using tags (CBOR Sequences, semantic tags) will error.

## Tips

- For sending data to a plugin, CBOR is preferable to JSON because it
  preserves bytes natively and is faster to parse.
- Don't rely on `repr`-based fallbacks for non-data types; they are not
  stable across Typst versions.
- `cbor.decode(...)` is **deprecated** — pass bytes directly to `cbor(...)`.
