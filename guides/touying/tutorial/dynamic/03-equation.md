# Dynamic 03 — Math Equation Animations

> Source: <https://touying-typ.github.io/docs/tutorials/dynamic/equation>

Touying lets you use `pause` and `meanwhile` **inside math equations** —
this is one of its standout features compared to Beamer / Polylux.

## Simple animation

Inside a `$ ... $` block, the bare words `pause` and `meanwhile` (without
`#`) are recognised as animation markers:

```typst
#slide[
  Touying equation with pause:
  $
    f(x) &= pause x^2 + 2x + 1  \
         &= pause (x + 1)^2  \
  $
  #meanwhile
  Touying equation is very simple.
]
```

You can also write `#pause` or `#pause;` inside the equation if you prefer
the explicit form.

The equation is rendered step-by-step, perfect for guiding through a
derivation in a presentation.

## Complex animation

Mark-style `only` / `uncover` / `alternatives` work inside equations too,
but you need callback style to read `self.subslide`:

```typst
#slide(repeat: 3, self => [
  #let (uncover, only, alternatives) = utils.methods(self)
  $
    f(x) &= pause x^2 + 2x + uncover("3-", 1)  \
         &= pause (x + 1)^2  \
  $
])
```

Here `uncover("3-", 1)` reveals the `+ 1` only from subslide 3 onward.

## Example

See [`examples/03-equation/03-equation.typ`](./examples/03-equation/03-equation.typ).

## Pitfalls

- The bare-word `pause` only works inside `$ ... $`. At the slide level,
  use `#pause`.
- `touying-equation(eq, ...)` is a lower-level helper — usually you don't
  need to call it directly.
- Inside an equation, `#alternatives[a][b]` typesets each alternative as
  inline math. Use `text` if you need plain text in one alternative.
