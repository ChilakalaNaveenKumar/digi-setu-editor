# Dynamic 04 — Cover Function

> Source: <https://touying-typ.github.io/docs/tutorials/dynamic/cover>

Both `#uncover` and `#pause` use the **`cover` function** to conceal not-yet-
revealed content. The `cover` function is a method stored at
`self.methods.cover`.

## Default — `hide`

The default `cover` is Typst's [`hide`](https://typst.app/docs/reference/layout/hide/),
which makes content invisible without affecting layout.

## Override the cover function

Set your own via `config-methods`:

```typst
config-methods(cover: (self: none, body) => hide(body))
```

## Hack — handle `enum` and `list` markers

Typst's default `hide` does not hide list bullets / enum numbers (see
[touying-typ/touying#10](https://github.com/touying-typ/touying/issues/10)).
The known workaround is to scale to zero width:

```typst
config-methods(cover: (self: none, body) => box(scale(x: 0%, body)))
```

## Semi-transparent cover

Touying ships a built-in semi-transparent option:

```typst
config-methods(cover: utils.semi-transparent-cover.with(alpha: 85%))
```

Tune transparency via `alpha:`. Internally this is:

```typst
#let semi-transparent-cover(self: none, constructor: rgb, alpha: 85%, body) = {
  cover-with-rect(
    fill: update-alpha(
      constructor: constructor,
      self.page.fill,
      alpha,
    ),
    body,
  )
}
```

It draws a coloured rectangle over the body using the page background
color with reduced alpha, so the hidden content "fades" instead of
disappearing.

> **Warning.** `transparent-cover` does **not** preserve text layout the
> way `hide` does — it adds an extra `box` layer. Long lines may reflow
> differently when uncovered.

## Example

See [`examples/04-cover/04-cover.typ`](./examples/04-cover/04-cover.typ).

## Pitfalls

- `cover` always receives `self: none` and `body` — keep that signature
  even for custom implementations.
- Switching `cover` mid-presentation requires `touying-set-config.with(
  config-methods(cover: ...))`. Once switched, all subsequent `#uncover`
  / `#pause` use the new behaviour.
- `utils.semi-transparent-cover` reads `self.page.fill` to compute the
  cover colour — if you set a `config-page(fill: ...)` override, the
  cover follows it automatically.
