# Dynamic 01 — Simple Animations

> Source: <https://touying-typ.github.io/docs/tutorials/dynamic/simple>

Touying provides two markers for the simplest reveal pattern: `#pause` and
`#meanwhile`.

## `#pause`

Splits the slide so everything after `#pause` appears on the next subslide.

```typst
#slide[
  First #pause Second
  #pause
  Third
]
```

This produces three subslides — `"First"` then `"First Second"` then
`"First Second Third"`. `#pause` may appear inline or on its own line.

## `#meanwhile`

Sometimes you want extra content to appear *with* a `#pause` step rather
than between two. `#meanwhile` resets the running subslide pointer to the
moment of the most recent `#pause`:

```typst
#slide[
  First
  #pause
  Second
  #meanwhile
  Third
  #pause
  Fourth
]
```

This produces only **two** subslides:

| Subslide | Visible |
| -------- | ------- |
| 1 | "First" + "Third" |
| 2 | "Second" + "Fourth" |

## Example

See [`examples/01-simple/01-simple.typ`](./examples/01-simple/01-simple.typ).

## Pitfalls

- `#pause` and `#meanwhile` are **show-rule metadata**. They cannot live
  inside a `context { ... }` block, inside a `raw {}`, or inside a CeTZ
  canvas (use `touying-reducer` for those — see
  [`05-other.md`](./05-other.md)).
- `#pause` works at the slide level **and** inside math equations
  (rendered as `pause`/`meanwhile` words — see
  [`03-equation.md`](./03-equation.md)).
- Inside `#item-by-item[...]` (lists) `#pause` is implicit per item; you
  do not need to add it manually.
