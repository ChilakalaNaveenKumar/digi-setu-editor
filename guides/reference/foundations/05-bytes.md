# Foundations / 05 — `bytes`

> **Typst version:** 0.14.2
> **Source page:** <https://typst.app/docs/reference/foundations/bytes/>
> **Audience:** an LLM agent. Original prose; technical facts about the `bytes` type. All examples below are verified to compile clean with `typst 0.14.2` (see `examples/05-bytes/`).

---

## What it is

`bytes` is a contiguous, immutable sequence of unsigned 8-bit values (0–255). Conceptually it's an "array of bytes", but stored in a packed, dedicated representation that is dramatically more memory-efficient than a real `array` of integers. Use it whenever you handle binary data — file contents from `read(...)`, image buffers, etc.

- **Example (constructing):** [`01-bytes-construct.typ`](./examples/05-bytes/01-bytes-construct.typ)
- **Example (slicing & converting):** [`02-bytes-slice-and-convert.typ`](./examples/05-bytes/02-bytes-slice-and-convert.typ)

---

## Constructor

`bytes(value) -> bytes`

| Input type | Behavior |
|---|---|
| `str` | Encode the string as **UTF-8**. |
| `array` of `int` | Each int must be in `0..=255`; copied directly into the packed representation. |
| `bytes` | Identity (returns the same value). |

Any other input type is a type error.

---

## Conversions out

| Goal | Use |
|---|---|
| Decode bytes to a string (assumes UTF-8) | `str(bytes_value)` — errors if not valid UTF-8. |
| Get an `array` of integer byte values | `array(bytes_value)` — slow & big; use only when you need element-by-element scripting. |
| Iterate one byte at a time | `for b in bytes_value { … }` (each `b` is an `int`). |

## Methods

| Method | Returns | Notes |
|---|---|---|
| `b.len()` | `int` | Number of bytes (NOT characters — multi-byte UTF-8 chars count as multiple bytes). |
| `b.at(index)` | `int` | Byte at the given index. |
| `b.at(index, default: x)` | `int` or `x` | Returns `x` if `index` is out of bounds. |
| `b.slice(start, end)` | `bytes` | Sub-range, `start` inclusive, `end` exclusive. |
| `b.slice(start, count: n)` | `bytes` | Same as `slice(start, start + n)`; mutually exclusive with `end`. |

---

## Reading binary data from a file

`read(path, encoding: none)` returns `bytes` (the `none` encoding disables UTF-8 decoding). Without `encoding: none`, `read(path)` returns a `str`. So:

| Goal | Call |
|---|---|
| Treat file as text | `read("config.json")` → `str` |
| Treat file as raw binary | `read("logo.png", encoding: none)` → `bytes` |

---

## Pitfalls

1. **`len()` is bytes, not characters.** `bytes("Héllo").len()` is 6, not 5, because `é` is two UTF-8 bytes.
2. **`str(bytes(...))` requires valid UTF-8.** Slicing in the middle of a multi-byte character will produce invalid UTF-8 and `str(...)` will error. If you need UTF-8-aware slicing, decode first and use `str` methods.
3. **Don't store huge byte buffers as `array` of int.** Stay in `bytes` form for any non-trivial binary data — the `array` representation is many times larger.
4. **Indices must be in range** unless you pass `default:`. Out-of-bounds is a hard error otherwise.

---

## Self-check

1. Is your input to `bytes(...)` a `str`, an `array` of int (each 0..255), or another `bytes`? (Anything else errors.)
2. If you `read(...)` a binary file, did you pass `encoding: none`?
3. If you slice and re-encode as `str`, do your slice boundaries land on character boundaries?
4. Does it compile? (`typst compile path.typ /tmp/out.pdf`)
