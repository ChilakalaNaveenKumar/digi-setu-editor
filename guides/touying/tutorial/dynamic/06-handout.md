# Dynamic 06 — Handout Mode

> Source: <https://touying-typ.github.io/docs/tutorials/dynamic/handout>

Handout mode collapses every animation subslide into a **single page per
logical slide**, which is what you want when exporting a printable PDF
for the audience.

## Enabling handout mode

```typst
#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-common(handout: true),
)

= Title
== Animated Slide
First item.
#pause
Second item (won't generate a separate page in handout mode).
#pause
Third item.
```

By default, handout mode keeps **only the last subslide** of each slide —
i.e. the fully revealed state.

## Choosing which subslides to keep

Use `handout-subslides` to override the default:

```typst
// Keep only the first subslide
config-common(handout: true, handout-subslides: 1)

// Keep first and last subslide
config-common(handout: true, handout-subslides: (1, -1))

// Keep a string-style range
config-common(handout: true, handout-subslides: "1-2")
```

The string syntax matches `only`/`uncover` (see
[`02-complex.md`](./02-complex.md)).

## Handout-only slides

Tag a heading with `<touying:handout>` to make it appear **only** when
`handout: true`:

```typst
== Extra Notes for Handout <touying:handout>
This slide is included only when `handout: true`.
```

The opposite (a slide that does **not** appear in handout mode) can be
achieved by wrapping it in a deferred config:

```typst
== Live Only
#show: touying-set-config.with(defer: true, config-common(handout: false))
```

…but the more idiomatic way is to live-build with `handout: false` and
re-build with `handout: true` for the export.

## Workflow tip

Common pattern — leave `handout: false` while presenting, switch to
`handout: true` when exporting the audience PDF:

```typst
// During presentation
#show: my-theme.with(config-common(handout: false))

// When building the handout PDF
#show: my-theme.with(config-common(handout: true))
```

If you use `touying-exporter` (see
[`../../external/01-touying-exporter.md`](../../external/01-touying-exporter.md))
you can pass `--sys-inputs '{"handout":"true"}'` and read it via
`sys.inputs.at("handout", default: "false")`.

## Example

See [`examples/06-handout/06-handout.typ`](./examples/06-handout/06-handout.typ).

## Pitfalls

- Handout mode keeps **the last** subslide by default, **not the first**.
- `handout-subslides` indices are 1-based; negative indices count from
  the end (`-1` = last).
- `<touying:handout>` works on **headings**, not on `#slide[...]` blocks.
  For block slides, gate visibility manually with
  `if config-common-handout { ... }` or the deferred-config trick.
