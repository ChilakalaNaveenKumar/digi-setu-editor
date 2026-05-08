# `display-icon`

Whether to display the *icon* of the language in the language pill. Only
applies if you're using the default language-block formatter
([`lang-format: auto`](./28-lang-format.md)).

| Field | Value |
| ----- | ----- |
| Type | `bool` |
| Default | `true` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(
  display-icon: false,
  languages: (
    py: (name: [Python], color: green, icon: "🐍"),
  ),
)
```py
print('Hello, world!')
print('Goodbye, world!')
```
```

The result shows just the name ("Python") — no 🐍 icon.

See [`examples/30-display-icon/30-display-icon.typ`](./examples/30-display-icon/30-display-icon.typ).

## Related

- [`29-display-name.md`](./29-display-name.md), [`16-languages.md`](./16-languages.md).
