# `lang-format`

The formatter for the language pill.

- `none` does not display the language pill at all.
- `auto` uses the default formatter (the rounded coloured pill you see
  in every example).
- A function takes three arguments and returns content:

  | Arg | Meaning |
  | --- | ------- |
  | `lang` | the language key (e.g. `py`) |
  | `icon` | the language icon, can be `none` or empty content |
  | `color` | the language colour |

| Field | Value |
| ----- | ----- |
| Type | `type(auto)`, `none`, or `function` |
| Default | `auto` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

> **Info** — The language formatter should avoid using state, as this
> can lead to quadratic execution time (see typst/typst #5220). When set
> to `auto`, codly uses an inlined function to avoid using states.

## Example

```typst
*Default formatter:*
```py
print('Hello, world!')
```

*Function mapping:*
#codly(lang-format: (_, _, _) => [No!])
```py
print('Hello, world!')
```
```

See [`examples/28-lang-format/28-lang-format.typ`](./examples/28-lang-format/28-lang-format.typ).

## Related

- [`16-languages.md`](./16-languages.md),
  [`23-lang-inset.md`](./23-lang-inset.md),
  [`24-lang-outset.md`](./24-lang-outset.md),
  [`25-lang-radius.md`](./25-lang-radius.md),
  [`26-lang-stroke.md`](./26-lang-stroke.md),
  [`27-lang-fill.md`](./27-lang-fill.md).
