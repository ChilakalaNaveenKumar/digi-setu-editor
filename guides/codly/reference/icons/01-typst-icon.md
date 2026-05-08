# `typst-icon` — Built-in Typst Language Icon

Codly ships with a language definition for the **Typst** language itself:
a name, colour, and the proper Typst icon. Use the `typst-icon` value to
spread that definition into your `languages:` dictionary.

> **Info** — `typst-icon` is a *variable*, not a function — read with
> `typst-icon`, do not call it.

## Signature

```text
typst-icon: dictionary
```

It is shaped exactly like an entry of [`languages`](../codly/16-languages.md):

```text
typst-icon: ( typ: ( name: "Typst", color: <typst-blue>, icon: <typst-icon-glyph> ) )
```

> **Info** — You can use the `..` spread operator to include it in your
> own languages dictionary.

## Example

```typst
#codly(languages: typst-icon)
```typ
= Here's a title
Hello, world!
```
```

To combine it with [`@preview/codly-languages`](https://typst.app/universe/package/codly-languages):

```typst
#import "@preview/codly-languages:0.1.7": *

#codly(languages: (..codly-languages, ..typst-icon))
```

See [`examples/01-typst-icon/01-typst-icon.typ`](./examples/01-typst-icon/01-typst-icon.typ).

## Pitfalls

- The Typst icon glyph requires Codly's bundled icon font (Tabler
  Icons). It is included with the package; just compile in any normal
  Typst environment.
- Spreading order matters: later entries win, so
  `(..codly-languages, ..typst-icon)` overrides any pre-existing
  `codly-languages.typ` entry.

## Related

- [`../codly/16-languages.md`](../codly/16-languages.md),
  [`00-icons-overview.md`](./00-icons-overview.md).
