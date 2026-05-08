# `math.upright` / `italic` / `bold` — math letterforms

Switch between the OpenType-encoded **letterform variants** in the active math font. These are different from the regular `text(weight: "bold")` and `emph(...)` because math fonts have dedicated glyphs for these styles (with proper math metrics).

## Functions

| Function          | Effect                                            |
| ----------------- | ------------------------------------------------- |
| `upright(body)`    | Non-italic letters.                               |
| `italic(body)`     | Italic letters (already the default for roman + lowercase Greek). |
| `bold(body)`       | Bold variant.                                     |

These can be combined: `bold(upright(A))` for bold upright, etc.

## When to use which

- Use `upright` for **fixed words** that happened to be entered as bare identifiers — e.g. `upright(d)x` for the calculus differential `d`.
- Use `italic` to force italic on quoted text or operator names that default to upright.
- Use `bold` to highlight definitions or emphasized symbols.

## Examples (compile-verified)

- `examples/16-styles/01-styles.typ` — upright vs default, bold, side-by-side comparison, forcing italic on quoted text.

## Reference

https://typst.app/docs/reference/math/styles/
