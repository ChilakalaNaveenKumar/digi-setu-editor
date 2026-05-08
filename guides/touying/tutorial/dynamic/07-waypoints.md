# Dynamic 07 — Waypoints

> Source: <https://touying-typ.github.io/docs/tutorials/dynamic/waypoints>

Waypoints let you name positions in a slide's animation timeline and
reference them by **label** instead of hard-coded subslide numbers.
Inserting a `#pause` before a waypoint shifts everything that follows
automatically — no more counting subslides by hand.

## Basic usage

Drop a `#waypoint(<label>)` to mark a named position; reference it from
`#uncover` or `#only`:

```typst
#slide[
  Base content.
  #waypoint(<step-a>)
  #uncover(<step-a>)[Uncovered from step-a.]
  #waypoint(<step-b>)
  #only(<step-b>)[Only during step-b.]
]
```

Each *advancing* waypoint (the default) creates a new subslide, so here
`<step-a>` fires on subslide 2 and `<step-b>` on subslide 3.

## Implicit waypoints

When you pass a fresh label directly to `#uncover`, `#only`, or
`#item-by-item`, an implicit waypoint is created automatically — no
separate `#waypoint(...)` call needed:

```typst
#slide[
  First content.
  #uncover(<reveal>)[Appears from here.]
  #only(<final>)[Only on the last step.]
]
```

The implicit waypoint is registered once per label (first occurrence wins).

## `item-by-item` with waypoints

`#item-by-item` accepts a label as `start`. Items reveal starting from
that waypoint:

```typst
#slide[
  #item-by-item(start: <list>)[
    - Alpha
    - Beta
    - Gamma
  ]
  #only(<done>)[All items revealed.]
]
```

This produces 4 subslides: items appear on 2, 3, 4 (the implicit
`<list>` waypoint advances to subslide 2), and `<done>` fires on
subslide 5.

## Non-advancing waypoints

`advance: false` marks a position **without** creating a new subslide:

```typst
#slide[
  #waypoint(<here>, advance: false)
  Content at the current position.
]
```

## Waypoint markers (`wp-m`)

Reference parts of a waypoint's range:

| Marker | Meaning |
| ------ | ------- |
| `from-wp(<l>)` | All subslides following the first subslide of `<l>`. |
| `until-wp(<l>)` | All subslides up to the last subslide of `<l>`. |
| `get-first(<l>)` | The first subslide of `<l>`. |
| `get-last(<l>)` | The last subslide of `<l>`. |
| `prev-wp(<l>)` | The waypoint immediately before `<l>`. |
| `next-wp(<l>)` | The waypoint immediately after `<l>`. |
| `not-wp(<l>)` | All subslides **not** in `<l>`'s range. |

```typst
#slide[
  #waypoint(<mid>)
  #uncover(<mid>)[Visible during mid.]
  #waypoint(<end>)
  #uncover(from-wp(<mid>))[From mid onward.]
  #only(prev-wp(<end>))[Only before end starts.]
]
```

Combine markers freely:

```typst
#slide[
  #waypoint(<mid>, advance: false)
  #uncover(<mid>)[Visible during mid.]
  #pause
  Second mid.
  #waypoint(<end>)
  End.
  #only(not-wp(get-first(<mid>)))[Soon finished.]
]
```

## Complex example

A waypoint can be referenced from outside the column it was defined in,
which is useful for two-column slides:

```typst
#slide(composer: (1fr, 1fr))[
  #item-by-item(start: <steps>)[
    - Step one
    - Step two
    - Step three
  ]
  #pause
  Some remark.
  #uncover(<done>)[All done!]
][
  #alternatives(at: (<steps>, <done>))[
    _Working through the steps..._
  ][
    _Complete!_
  ]
]
```

## Explicit waypoint starts

`#waypoint(<label>, start: <other-label-or-int>)` lets you fix an explicit
start position:

```typst
#slide(composer: (1fr, 1fr))[
  #item-by-item(start: <steps>)[
    - Step one
    - Step two
    - Step three
  ]
  #pause
  Some remark.
  #uncover(<done>, start: 4)[All done, even before the remark!]
][
  #waypoint(<parallel>, start: <done>)
  Explaining stuff.
  #pause
  More explanation.
]
```

## Example

See [`examples/07-waypoints/07-waypoints.typ`](./examples/07-waypoints/07-waypoints.typ).
For a comprehensive set of waypoint patterns (callback-style, CeTZ /
Fletcher integration, `recall-subslide`, edge cases), see the upstream
[`examples/waypoints.typ`](https://github.com/touying-typ/touying/blob/main/examples/waypoints.typ).

## Pitfalls

- Labels are *Typst labels* — `<step-a>`, **not** strings.
- `#waypoint(<l>, advance: false)` is the right tool for "name the current
  position without creating a new subslide".
- Waypoints capture **all subslides** following them until the next
  waypoint. So `#uncover(<mid>)` reveals on every subslide from `<mid>`'s
  first to `<mid>`'s last (which is one before the next waypoint).
- Waypoints work in handout-subslides (since v0.7.0).
