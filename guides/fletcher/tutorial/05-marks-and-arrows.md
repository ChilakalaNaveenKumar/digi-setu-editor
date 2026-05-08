# 5 — Marks and arrows

Marks (arrowheads, dots, hooks) decorate an edge. They are specified
by the `marks:` option of `edge()`, but Fletcher provides a powerful
**mark shorthand string** for the common case.

## The shorthand grammar

A mark shorthand is a string `M1 L M2 [L M3 ...]`, where:

- `Mi` is a mark name (or empty).
- `L` is a line style: `-` (single), `=` (double), `==` (triple),
  `--` (dashed), `..` (dotted), `~` (squiggly).

Examples that look like the unicode arrows in math mode:

| Shorthand | Looks like |
| --------- | ---------- |
| `"->"`    | → |
| `"=>"`    | ⇒ |
| `"==>"`   | ⇛ |
| `"\|->"`  | ↦ |
| `"->>"`   | ↠ |
| `"hook->"`| ↪ |

Other common combinations:

| Shorthand | Notes |
| --------- | ----- |
| `">>-->"` | reversed double-head + single arrow at end |
| `"\|\|-/-\|>"` | bar–slash–open arrow, on a single stroke |
| `"o..O"`  | small circle to big circle, dotted line |
| `"hook'-x-}>"` | flipped hook + cross + open arrow on a dashed line |
| `"-*-harpoon"` | unmarked tail, star midpoint, harpoon at tip |

Append `'` to **flip** the mark across the edge: `"hook'->"` flips
the hook downward.

## The default mark catalog

| Glyph family | Names |
| ------------ | ----- |
| `head` doublehead triplehead | `>`, `<`, `>>`, `<<`, `>>>`, `<<<` |
| harpoon, straight, solid | `harpoon`, `straight`, `solid` |
| stealth, latex, cone | `\|>`, `<\|`, `}>`, `<{`, `cone` |
| circle, square, diamond | `o`, `O`, `*`, `@`, `[]`, `<>` |
| bar, cross | `\|`, `\|\|`, `\|\|\|`, `/`, `\\`, `x`, `X` |
| bracket, parenthesis | `[`, `]`, `(`, `)` |
| hook, hooks | `hook`, `hooks` |
| crowfoot, n, 1 | `crowfoot`, `n`, `n!`, `n?`, `1`, `1!`, `1?` |

The full catalog is held in the `fletcher.MARKS` state — read with
`context fletcher.MARKS.get()`.

## Example

```typst
#diagram(
  spacing: 1cm,
  edge((0,0), (1,0), "->"),
  edge((0,1), (1,1), "=>"),
  edge((0,2), (1,2), "hook'-/->>"),
  edge((0,3), (1,3), "o..O"),
)
```

See [`examples/05-marks-and-arrows/05-marks-and-arrows.typ`](examples/05-marks-and-arrows/05-marks-and-arrows.typ).

## Pitfalls

- The mark shorthand is positional but Fletcher *guesses* whether a
  string is a mark, a label, or a vertex shorthand. If a label is a
  string that looks like a shorthand (`"=>"`), pass it via
  `label: "=>"` to disambiguate.
- Triple strokes (`==>`) automatically scale the arrowhead larger to
  match the visual weight; override with `mark-scale:`.
- A flipped mark (`hook'`) is NOT the same as a reversed mark (`<`).
  Flip = mirror across the line; reverse = point the other way.

## Next

[`06-custom-marks.md`](06-custom-marks.md) — fully custom mark
objects.
