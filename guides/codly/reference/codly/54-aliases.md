# `aliases`

Creates aliases between languages, allowing them to share *syntax
highlighting* but have separate *display names and icons*. The classic
use case is `cuda` and `c++` — same highlighter, different language pill.

| Field | Value |
| ----- | ----- |
| Type | `dictionary` |
| Default | `(:)` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#import "@preview/codly-languages:0.1.7": *

#codly(
  languages: codly-languages,
  aliases: ("cuda": "c++"),
)
```cuda
int main() {
  std::cout << "Hello, World!" << std::endl;
  return 0;
}
```
```

The block is highlighted as C++, but the language pill says **CUDA** (the
key with which you opened the raw block).

See [`examples/54-aliases/54-aliases.typ`](./examples/54-aliases/54-aliases.typ).

## Pitfalls

- The dictionary keys are the *aliased* language names (the names you
  use in raw-block fences). Values are the *real* highlighter language
  names. So `("cuda": "c++")` means "treat `cuda` as `c++` for
  highlighting".
- Aliases interact with [`languages`](./16-languages.md): the language
  pill picks up the entry keyed by the **alias**, not the target. Define
  your `cuda` entry under `languages.cuda`.

## Related

- [`16-languages.md`](./16-languages.md).
