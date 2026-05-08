# Dynamic 02 — Complex Animations (`only` / `uncover` / `alternatives`)

> Source: <https://touying-typ.github.io/docs/tutorials/dynamic/complex>

Touying supports the [Polylux](https://polylux.dev/book/dynamic/syntax.html)
animation primitives `only`, `uncover`, and `alternatives` in two flavours:
mark-style and callback-style.

## Mark-style functions

The simplest form — these functions act as inline annotations at the slide
top level:

```typst
At subslide #touying-fn-wrapper((self: none) => str(self.subslide)), we can
use #uncover("2-")[`#uncover` function] for reserving space,
use #only("2-")[`#only` function] for not reserving space,
#alternatives[call `#only` multiple times \u{2717}][use `#alternatives` function #sym.checkmark] for choosing one of the alternatives.
```

This works at the slide top level but **not inside `context { ... }`** —
inside `context` you must use the callback style.

## Callback-style functions

Touying's callback-style slide takes a `(self) => content` function and
gives you `self.subslide`, `self.subslides`, and method bindings:

```typst
#slide(repeat: 3, self => [
  #let (uncover, only, alternatives) = utils.methods(self)
  At subslide #self.subslide, we can
  use #uncover("2-")[`#uncover` function] for reserving space,
  use #only("2-")[`#only` function] for not reserving space,
  #alternatives[call `#only` multiple times \u{2717}][use `#alternatives` function #sym.checkmark] for choosing one of the alternatives.
])
```

The `#let (uncover, only, alternatives) = utils.methods(self)` line is the
recommended pattern — `utils.methods(self)` returns the same primitives
*bound* to the current `self` so they read `self.subslide` correctly.

> **Warning.** You **must** specify `repeat: N` when using callback style.
> Touying cannot infer how many subslides `only`/`uncover`/`alternatives`
> need when accessed through `utils.methods` bindings.

## `only`

`#only(index, body)` is either `body` or `none` — it disappears entirely
on non-matching subslides (no space reserved).

The `index` may be:

- An int: `1`, `2`, `3`.
- A range string: `"2-"`, `"-3"`, `"2-3"`, `"1,3"`.
- `auto` — current position when `only` is encountered.
- `"h"` (string version of `auto`), `"h-"`, `"-h"`.
- An inverse: `"!2"`, `"!h"`, `"!2-4"` — appear on every subslide
  *except* the listed ones (does not increment the subslide count).

For waypoints (label-based indexing) see [`07-waypoints.md`](./07-waypoints.md).

## `uncover`

`#uncover(index, body)` is `body` on matching subslides and `cover(body)`
otherwise — space is reserved either way. The `cover` function defaults to
[`hide`](https://typst.app/docs/reference/layout/hide/), but is overridable
(see [`04-cover.md`](./04-cover.md)).

`#pause` is essentially syntactic sugar over `uncover`.

## `alternatives`

`alternatives` shows different content on different subslides, sized to
the largest alternative:

```typst
#slide(repeat: 3, self => [
  #let (uncover, only, alternatives) = utils.methods(self)
  #alternatives[Ann][Bob][Christopher]
  likes
  #alternatives[chocolate][strawberry][vanilla]
  ice cream.
])
```

`alternatives` accepts:

- `start: 2` — begin from subslide 2 (default 1).
- `repeat-last: true` — keep showing the last alternative on later subslides.
- `position: center + horizon` — alignment within the bounding box.

See <https://polylux.dev/book/dynamic/alternatives.html> for full coverage.

## Example

See [`examples/02-complex/02-complex.typ`](./examples/02-complex/02-complex.typ).

## Pitfalls

- Mark-style `#uncover` / `#only` panic inside `context { ... }`. Switch
  to callback style.
- `#alternatives` measures **all** alternatives to size the box. If one is
  much taller, that is the height the slot occupies on every subslide.
- `repeat: auto` (the default) only works without `utils.methods`
  bindings — set it explicitly when binding via `let (only, ...) =
  utils.methods(self)`.
