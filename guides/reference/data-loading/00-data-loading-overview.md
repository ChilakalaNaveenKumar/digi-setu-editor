# Data Loading – Overview

The data-loading module reads structured or plain data from external
files into Typst values you can iterate, format, and template against —
essential when your document is generated from an experiment, an
external source-of-truth, or a build pipeline.

## What lives in this module

| Function | Source format          | Returns                                              |
| -------- | ---------------------- | ---------------------------------------------------- |
| `read`   | UTF-8 text or raw bytes | `str` (default) or `bytes` (`encoding: none`).       |
| `csv`    | Comma-separated values | `array<array<str>>` (or `array<dict<str, str>>`).    |
| `json`   | JSON                   | Whatever the JSON describes.                         |
| `yaml`   | YAML                   | Whatever the YAML describes.                         |
| `toml`   | TOML                   | Always a dictionary (TOML documents are tables).     |
| `cbor`   | CBOR                   | Whatever the CBOR describes.                         |
| `xml`    | XML                    | Array of strings/dicts representing the tree.        |

Each loader accepts either a **path** (string, resolved like other Typst
file paths) or **raw bytes** — handy when bytes were produced by `read`,
a `plugin`, or another loader.

## Encoding (`json`, `yaml`, `toml`, `cbor`)

Several modules also expose `.encode(value)` for serializing Typst values
back to bytes/strings:

| Encoder            | Output type                                  |
| ------------------ | -------------------------------------------- |
| `json.encode(v, pretty: true)` | `str`                            |
| `yaml.encode(v)`   | `str`                                        |
| `toml.encode(v, pretty: true)` | `str` (input must be a dict)     |
| `cbor.encode(v)`   | `bytes`                                      |

`xml`, `csv`, and `read` are read-only.

These encoders are most useful for passing structured data to a `plugin`
that expects a particular wire format (CBOR is the recommended one for
binary).

## Type conversions

Loaders convert source types into the natural Typst counterparts:

| Source kind             | Typst value                                  |
| ----------------------- | -------------------------------------------- |
| boolean                 | `bool`                                       |
| integer                 | `int` (loses precision past ±2⁶³−1)          |
| number / float          | `float`                                      |
| string                  | `str`                                        |
| array / sequence        | `array`                                      |
| object / map / table    | `dictionary`                                 |
| `null` / `~` / empty    | `none`                                       |

When *encoding* Typst values to JSON/TOML/YAML/CBOR:

- `symbol` becomes a string.
- `bytes` round-trips as a string via `repr` for JSON/TOML/YAML — for
  binary data prefer `cbor`.
- `content` becomes a structured dictionary describing its tree (best
  effort).
- Anything else (`length`, `color`, ...) becomes a debug `repr` string.

> `repr` output is **for debugging only** — it is not stable across
> Typst versions. Don't write data pipelines that rely on it.

## Deprecation watch (Typst 0.13+)

`json.decode(bytes)`, `csv.decode(bytes)`, `yaml.decode(bytes)`,
`toml.decode(bytes)`, `cbor.decode(bytes)`, `xml.decode(bytes)`, and
`image.decode(bytes)` are all **deprecated**. Pass bytes directly to the
loader instead — `json(my-bytes)`, `csv(my-bytes)`, etc. The `*.decode`
forms still work and emit warnings; they will be removed in 0.15.

## Picking a format

| When you have...                            | Reach for                                |
| ------------------------------------------- | ---------------------------------------- |
| Tabular data with a header row              | `csv(..., row-type: dictionary)`         |
| Configuration / front-matter style          | `toml`                                   |
| Hand-written human config                   | `yaml`                                   |
| Programmatic data interchange               | `json`                                   |
| Binary-friendly machine interchange         | `cbor`                                   |
| Hierarchical structured documents           | `xml`                                    |
| Plain text or raw bytes                     | `read`                                   |

## Path resolution

All loaders use the same path rules as `image` and other file-reading
functions: paths are relative to the current source file. Absolute
paths and project-relative paths are also supported. See
[Paths](https://typst.app/docs/reference/syntax/#paths) for details.
