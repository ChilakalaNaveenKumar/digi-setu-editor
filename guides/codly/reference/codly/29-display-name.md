# `display-name`

Whether to display the *name* of the language in the language pill. Only
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
  display-name: false,
  languages: (
    py: (name: [Python], color: green, icon: "🐍"),
  ),
)
```py
print('Hello, world!')
print('Goodbye, world!')
```
```

The result shows just the icon (🐍) — no "Python" text.

See [`examples/29-display-name/29-display-name.typ`](./examples/29-display-name/29-display-name.typ).

## Related

- [`30-display-icon.md`](./30-display-icon.md), [`16-languages.md`](./16-languages.md).
