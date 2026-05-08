# `languages`

The language definitions to use for language-pill formatting. A
dictionary where the keys are the language names and each value is
another dictionary containing:

| Key | Type | Notes |
| --- | ---- | ----- |
| `name` | content / showable | The "pretty" name of the language. |
| `color` | color | Optional. Falls back to [`default-color`](./17-default-color.md) when omitted. |
| `icon` | content | Optional. No icon is shown when omitted. |

If an entry is missing and language pills are enabled, Codly shows the
"un-prettified" language name with the default colour.

| Field | Value |
| ----- | ----- |
| Type | `dictionary` |
| Default | `(:)` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(
  languages: (
    py: (name: [Python], color: green, icon: "🐍"),
  ),
)
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)
fib(25)
```
```

### Pre-existing language definitions

There is a sister package
[`@preview/codly-languages`](https://typst.app/universe/package/codly-languages)
with definitions for many languages out of the box, officially endorsed
by the Codly author since November 2024:

```typst
#import "@preview/codly-languages:0.1.7": *
#codly(languages: codly-languages)
```rust
fn main() { println!("Hello, world!"); }
```
```

See [`examples/16-languages/16-languages.typ`](./examples/16-languages/16-languages.typ).

## Pitfalls

- The `name` is shown only when [`display-name: true`](./29-display-name.md).
- The `icon` is shown only when [`display-icon: true`](./30-display-icon.md).
- For unicode-PUA icons (Tabler, Font Awesome, …), see
  [`../icons/00-icons-overview.md`](../icons/00-icons-overview.md).

## Related

- [`17-default-color.md`](./17-default-color.md),
  [`28-lang-format.md`](./28-lang-format.md),
  [`29-display-name.md`](./29-display-name.md),
  [`30-display-icon.md`](./30-display-icon.md),
  [`54-aliases.md`](./54-aliases.md),
  [`../icons/01-typst-icon.md`](../icons/01-typst-icon.md).
