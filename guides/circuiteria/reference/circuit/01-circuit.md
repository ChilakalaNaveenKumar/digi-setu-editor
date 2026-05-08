# `circuit()` — The Block-Diagram Envelope

Draws a block circuit diagram. Returns `none` (it emits the figure as a
side-effect via the underlying CeTZ canvas).

> This function is also available at the package root as
> `circuiteria.circuit(...)`.

## Signature

```text
circuit(
  body:   none | array | element,
  length: length | ratio = 2em,
) -> none
```

## Parameters

- **`body`** — `none | array | element`. A code block in which `element.*`,
  `wire.*`, `gates.*`, and CeTZ `draw.*` functions have been called. Almost
  always you also `import circuiteria: *` at the top of the body so the
  short module names are in scope.
- **`length`** — `length | ratio`. The base unit; one Circuiteria unit
  equals this many points / ems. Default `2em`. (Internally this is forwarded
  to `cetz.canvas`'s `length:` argument.)

## Anchors

`circuit(...)` itself does not expose anchors — anchors live on the
`element.*`, `gates.*`, and `wire.*` calls *inside* the body. The circuit
envelope just contains them.

## Pitfalls

- **Always `import circuiteria: *` inside the body** so that `element`,
  `wire`, `gates`, and `util` resolve to the sub-modules.
- **`length:` does not accept `auto`.** Pass an explicit length or ratio.
- The envelope auto-sizes around its contents (via the underlying CeTZ
  canvas). There is no explicit `width` / `height`.
- Because Circuiteria is built on CeTZ, you can call any
  [`cetz.draw.*`](../../../cetz/reference/) function inside the body — for
  example `draw.circle((0, 0), radius: .1, name: "p")` to drop a labelled
  reference point. **`draw` is not re-exported by `import circuiteria: *`**,
  so add `#import "@preview/cetz:0.3.2": draw` at the top of your file when
  you need it (use the same `0.3.2` version Circuiteria depends on
  internally to avoid version skew).

## Example

See [`examples/01-circuit/01-circuit.typ`](./examples/01-circuit/01-circuit.typ).

## Related

- [`element/03-block.md`](../element/03-block.md) — the most general
  element you can place inside a `circuit`.
- [`wire/03-wire.md`](../wire/03-wire.md) — connect two ports inside a
  `circuit`.
- [`../../tutorial/01-getting-started.md`](../../tutorial/01-getting-started.md)
  — full first-principles walkthrough.
