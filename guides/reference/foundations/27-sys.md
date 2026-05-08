# `sys` — system / environment access

The `sys` module exposes data about the *running* Typst process. Two members today:

| Member        | Type        | Description                                                |
| ------------- | ----------- | ---------------------------------------------------------- |
| `sys.version` | `version`   | The Typst compiler version compiling this file.            |
| `sys.inputs`  | `dictionary`| CLI `--input key=value` flags. Values are **always strings**. |

## `sys.version`

Use it for version-gated polyfills and capability checks:

```typst
#if sys.version >= version(0, 13, 0) [
  // new behavior
] else [
  // legacy behavior
]
```

`.major`, `.minor`, `.patch` are direct field accessors; deeper components via `.at(idx)`. See `30-version.md` for the full `version` API.

## `sys.inputs`

```bash
typst compile --input title="My Doc" --input year=2026 file.typ
```

Inside `file.typ`:

```typst
#sys.inputs.title         // "My Doc"
#int(sys.inputs.year)     // 2026 (parse manually)
```

Values are always strings — for ints / bools / structured data, parse explicitly:

| Source          | Parser                                                  |
| --------------- | ------------------------------------------------------- |
| `"42"` → int    | `int(sys.inputs.n)`                                     |
| `"3.14"` → float| `float(sys.inputs.x)`                                   |
| `"true"` → bool | `sys.inputs.b == "true"` (no `bool("...")` constructor) |
| JSON blob       | `json.decode(sys.inputs.config)`                        |
| YAML blob       | `yaml.decode(sys.inputs.config)`                        |
| TOML blob       | `toml.decode(sys.inputs.config)`                        |

Values containing spaces must be quoted on the CLI (single OR double quotes work).

## Pitfalls

- **`sys.inputs` is empty without `--input` flags.** Always read with `.at("key", default: ...)` to avoid a missing-key error in tests / preview / CI runs that forget to pass the flag.
- **No type coercion.** `sys.inputs.year` is `"2026"` (string), never `2026` (int). Forgetting to wrap with `int()` produces silent bugs (string concatenation instead of arithmetic).
- **No environment variable access.** `sys` is intentionally minimal. If you need env vars, pass them through `--input`.
- **`sys.version` is the *compiler* version, not the package version**. For your own document's version metadata, define your own constant.

## Examples (compile-verified)

- `examples/27-sys/01-version-and-inputs.typ` — reading `sys.version` (full + named-field), version comparison, defensive `sys.inputs.at(..., default: ...)` access.

## Reference

- Official: https://typst.app/docs/reference/foundations/sys/
- `version` type: https://typst.app/docs/reference/foundations/version/
