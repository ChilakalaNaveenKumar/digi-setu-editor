# `core` — Slide Splitting + Animation Primitives

> Source: [src/core.typ](https://github.com/touying-typ/touying/blob/main/src/core.typ)

The core module owns the slide-splitting state machine and the animation
primitives.

## Slide functions

### `touying-slide(self: none, ..args, body) -> content`

The low-level slide renderer. Theme `slide(...)` functions ultimately
call this with a fully-merged `self`.

### `touying-slide-wrapper(callback) -> content`

Wraps a callback so that `self` is auto-injected. Standard pattern in
custom theme `slide(...)` definitions:

```typst
#let slide(title: auto, ..args) = touying-slide-wrapper(self => {
  // mutate self...
  touying-slide(self: self, ..args)
})
```

### `touying-slides(...config-dicts, body) -> content`

The show-rule entry point used inside theme functions:

```typst
show: touying-slides.with(
  config-page(...),
  config-common(slide-fn: slide),
  ..args,
)
```

## Animation primitives

### `pause`

Splits subsequent content onto a new subslide. Inline / standalone OK.

### `meanwhile`

Resets the running subslide pointer, so the next content sits at the
moment of the most recent `#pause`.

### `only(index, body)`

Body if the current subslide matches `index`, else `none`. Index syntax:
int / `"2-"` / `"2-3"` / `auto` / `"h"` / `"!2"` / `"!h"`.

### `uncover(index, body, cover-fn: ..)`

Body if matched, else `cover-fn(body)` (default uses the active `cover`
method). Optional `cover-fn:` lets you override per-call (used by
Fletcher integration).

### `alternatives(start: 1, repeat-last: true, position: center + horizon, ..bodies)`

Cycles through `bodies` across subslides, sized to the largest. See
[`../../tutorial/dynamic/02-complex.md`](../../tutorial/dynamic/02-complex.md).

### `appendix(body)` / `#show: appendix`

Stops the slide counter. Equivalent to
`touying-set-config.with(defer: true, config-common(appendix: true))`.

### `jump(n, relative: bool) -> content`

Unified animation control. `#pause` is `#jump(1, relative: true)`;
`#meanwhile` is `#jump(0, relative: true)`.

### `effect(modifier, index)[body]`

Applies `modifier` to `body` on subslides matching `index`:

```typst
#effect(text.with(fill: red), "2-")[Something]
```

`Something` is red on subslide 2 onward.

### `item-by-item(start: 1)[items]`

Reveal a list / enum / terms one item at a time. `start` may be an int
or a waypoint label.

## Special wrappers

### `touying-fn-wrapper((self: none) => content)`

Wrap an arbitrary computation so it runs at slide-render time with
access to `self`. Used internally by `touying-get-config`.

### `touying-reducer(reduce: fn, cover: fn).with(...)`

Bind a foreign drawing function (CeTZ canvas, Fletcher diagram) so that
animation markers inside it are honoured:

```typst
#let cetz-canvas = touying-reducer.with(
  reduce: cetz.canvas,
  cover: cetz.draw.hide.with(bounds: true),
)
```

See [`../../tutorial/dynamic/05-other.md`](../../tutorial/dynamic/05-other.md).

### `touying-recall(slide-id, subslide: none)`

Replay a previously-rendered slide (e.g. for a "remember this?" callback
later in the deck).

### `touying-equation(eq, ...)`

Lower-level helper for `pause` / `meanwhile` inside math equations.
Usually you write `pause` / `meanwhile` directly inside `$ ... $` and
this is invoked under the hood.

### `touying-mitex(mitex, eq)`

Like `touying-equation` but for LaTeX-source equations via `mitex`.
See [`../../integration/02-mitex.md`](../../integration/02-mitex.md).

### `touying-raw(lang: ..., raw-block)`

Animated `raw {}` block — `// pause` and `// meanwhile` comment markers
trigger subslides. See [`../../integration/05-codly.md`](../../integration/05-codly.md).

### `touying-disable-warnings` / `touying-enable-warnings`

Toggle Touying-emitted warnings.

## Waypoints

### `waypoint(<label>, advance: true, start: none) -> content`

Mark a named timeline position. `advance: false` to mark without
creating a new subslide. `start:` to fix an explicit start position.

### `from-wp(<l>)`, `until-wp(<l>)`, `get-first(<l>)`, `get-last(<l>)`, `prev-wp(<l>)`, `next-wp(<l>)`, `not-wp(<l>)`

Waypoint markers — pass to `only` / `uncover` for label-based subslide
ranges. See [`../../tutorial/dynamic/07-waypoints.md`](../../tutorial/dynamic/07-waypoints.md).

## Speaker notes

### `speaker-note[body]`

Per-slide speaker note. Visible only when
`config-common(show-notes-on-second-screen: ...)` is set; otherwise
suppressed in the output. Always attaches to the previous slide
(v0.7.3+).

## See also

- [`01-configs.md`](./01-configs.md) — for `touying-set-config` /
  `touying-get-config`.
- [`../../tutorial/dynamic/`](../../tutorial/dynamic/) — animation
  primitives in depth.
