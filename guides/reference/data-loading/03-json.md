# `json()` — Reading and Writing JSON

`json` parses a JSON document into Typst values. The companion
`json.encode(value, pretty: true)` produces a JSON string.

## Signature

```text
json(source: str | bytes)               -> any
json.encode(value: any, pretty = true)  -> str
```

## Decoding semantics

| JSON                | Typst                                            |
| ------------------- | ------------------------------------------------ |
| `null`              | `none`                                           |
| `true` / `false`    | `bool`                                           |
| Integer (whole)     | `int` (lossy past `±2⁶³−1`; becomes `float`)     |
| Float / non-whole   | `float`                                          |
| String              | `str`                                            |
| Array               | `array`                                          |
| Object              | `dictionary`                                     |

The result of `json("file.json")` matches the JSON value at the top
level — usually a dictionary or an array.

## Encoding semantics

`json.encode` accepts anything Typst can hold:

| Typst                                  | JSON                                        |
| -------------------------------------- | ------------------------------------------- |
| `bytes`                                | string via `repr` (debug only)              |
| `symbol`                               | string                                      |
| `content`                              | object describing the content tree          |
| Other types (`length`, `color`, ...)   | string via `repr` (debug only)              |
| Everything else                        | corresponding JSON value                    |

For binary data prefer [`cbor`](./01-cbor.md) — it preserves bytes
natively.

## Tips

- JSON does not preserve key order — don't rely on dictionary iteration
  order across encode / decode.
- `pretty: false` produces compact, single-line JSON (good for CI logs).
- `json.decode(...)` is **deprecated** — pass bytes directly to `json(...)`.

## Recipe: weather forecast

```typst
#let day = json("monday.json")     // {"temperature": 20, "unit": "C", "weather": "sunny"}
#day.temperature°#day.unit, #day.weather
```

JSON files are the most common interchange format for templates that
take parameters from a build pipeline.
