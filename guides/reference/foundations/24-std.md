# `std` — the standard-library escape hatch

`std` is the built-in module containing every globally accessible item in Typst (every element function, every value like `auto`/`none`/`luma`, etc.). It exists for two reasons.

## 1. Bypass shadowing

When a local binding (a parameter, a `let`, an import) overrides a built-in name, you've **shadowed** it. `std.<name>` always reaches the original.

```typst
#let title(text) = {
  // 'text' is now the parameter, not the text element.
  set std.text(weight: "bold")
  text
}
```

Common shadow culprits: `text`, `figure`, `link`, `box`, `table`, `image`, `par`. If a parameter accidentally shadows one of these, the function silently breaks at the next `set text(...)` because `text` is now content, not a function.

## 2. Capability checks / polyfills

`"name" in std` is `bool` — true if `name` is a top-level definition. Combine with `sys.version` to write code that runs on multiple Typst versions:

```typst
// 'pattern' was renamed to 'tiling' in 0.13. Same args, so just alias.
#let tiling = if "tiling" in std { tiling } else { pattern }

// Or branch on a version directly:
#if sys.version >= version(0, 13, 0) [
  // new path
] else [
  // legacy path
]
```

Use `dictionary(std).keys()` if you need to inspect what's available at runtime (rare).

## Pitfalls

- **`std` is a module, not a "standard prefix" you can import from.** You can't `#import std: *` to dump everything — those names are already in scope. `std` exists specifically for the unshadowed-access case.
- **Polyfills should match argument shape.** If the new function added a required parameter, an alias `let foo = if "foo" in std { foo } else { fallback-foo }` will break under the old version. Wrap the alias in your own helper that adapts the arguments.
- **`sys.version`** is the most reliable signal — `"name" in std` doesn't tell you which behavior to expect, only whether *some* binding called `name` exists.

## Examples (compile-verified)

- `examples/24-std/01-shadowed-access.typ` — function with `text` as parameter; `set std.text(...)` and `set std.par.line(...)` reach through the shadow.
- `examples/24-std/02-feature-detection.typ` — `"name" in std` capability checks; safe alias pattern; commented polyfill template.

## Reference

- Official: https://typst.app/docs/reference/foundations/std/
- `sys.version` for version-gated polyfills: https://typst.app/docs/reference/foundations/sys/
