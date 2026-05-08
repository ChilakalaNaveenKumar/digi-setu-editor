# `module` — collections of definitions

A module is a bundle of variables and functions grouped under a single namespace. Modules come from:

- **Built-in** modules (`std`, `calc`, `sys`, etc.).
- **File imports** — `#import "path.typ"`.
- **Package imports** — `#import "@preview/foo:1.2.3"` (resolves to a package's entrypoint file).
- **Plugins** — the result of calling `plugin(...)`.

## Importing

| Form                                | Effect                                                                                  |
| ----------------------------------- | --------------------------------------------------------------------------------------- |
| `#import "file.typ"`                | binds the module to a local name = the file's stem (e.g. `helpers`)                     |
| `#import "file.typ" as h`           | binds to an explicit local name `h`                                                     |
| `#import "file.typ": a, b`          | brings `a` and `b` directly into the current scope                                      |
| `#import "file.typ": *`             | brings **all** definitions into the current scope                                       |
| `#include "file.typ"`               | inlines the file's *content* (not its definitions) at this point                        |

Use `as <name>` whenever the filename stem isn't a clean identifier (digits at the start, dashes, dots, etc.) or you want a shorter local name.

## Accessing members

Field-access notation:

```typst
#import "helpers.typ" as h
#h.add(2, 3)
#h.pi-approx
```

## Introspection

| Operation                     | Result                                                              |
| ----------------------------- | ------------------------------------------------------------------- |
| `"name" in some-module`       | `bool` — true if the module exports a definition called `name`      |
| `dictionary(some-module)`     | `dict` — convert the module's exports into a dictionary             |

Combine these for **conditional access**:

```typst
#if "table" in std [
  #table(columns: 2)[a][b][c][d]
]
```

## Pitfalls

- `#import "file.typ"` (no `as`) only works as a binding when the file stem is a valid identifier. Files like `1-utils.typ` or `_helpers.typ` need `as`.
- `#include` is **not** an import — it inlines content into the current document. Don't reach for it when you actually want functions/variables.
- Modules are immutable. You can't add or remove definitions at runtime — you can only convert to a `dictionary` and work with that copy.
- Names starting with `_` are *still exported*. Privacy is convention only.

## Examples (compile-verified)

- `examples/17-module/helpers.typ` — tiny helper module used by the others.
- `examples/17-module/01-import-and-access.typ` — `as h`, member-list import, field access.
- `examples/17-module/02-introspect.typ` — `in` checks against a custom module and `std`, `dictionary(module).keys()`, conditional-access pattern.

## Reference

- Official: https://typst.app/docs/reference/foundations/module/
