# 01 — Getting Started

> **Circuiteria version:** 0.2.0 · **Source:** `manual (2).pdf` §1–§3.1

Circuiteria is invoked from any Typst document by importing the package and
wrapping your circuit code in a `circuit { ... }` block. This page walks
through the absolute minimum.

## Hello, Circuiteria

```typst
#import "@preview/circuiteria:0.2.0"

#circuiteria.circuit({
  import circuiteria: *
  element.block(
    x: 0, y: 0, w: 2, h: 2, id: "b1",
    ports: (
      west: ((id: "in1", name: "A"), (id: "in2", name: "B")),
      east: ((id: "out", name: "C"),),
    ),
  )
  wire.stub("b1-port-in1", "west")
  wire.stub("b1-port-in2", "west")
  wire.stub("b1-port-out", "east")
})
```

## Why import `circuiteria: *` *inside* the circuit

Circuiteria re-exports five names — `circuit`, `element`, `wire`,
`gates`, `util` — under the package root. Importing them inside the
`circuit({ ... })` body keeps those short names (`element`, `wire`, …)
scoped to the drawing instead of leaking into the surrounding document.

```typst
#circuiteria.circuit({
  import circuiteria: *      // element / wire / gates / util now in scope
  element.block(/* … */)
})
```

(You may also call sub-module functions through their long form
`circuiteria.element.block(...)` without importing — that is what the
upstream manual does on most pages.)

> **`draw` is *not* in this set.** If you want to drop CeTZ primitives
> like `draw.circle((0, 0), name: "p")` into the body, add an explicit
> `#import "@preview/cetz:0.3.2": draw` at the top of your file. Use
> `0.3.2` — that is the CeTZ version Circuiteria depends on internally,
> so the contexts stay compatible.

## The `<id>-port-<port-id>` anchor convention

Every element accepts a `ports:` dictionary keyed by cardinal direction
(`north`, `east`, `south`, `west`); each value is an array of port
dictionaries with at least an `id` field. After the element is placed,
each port becomes a named anchor:

```text
"<element-id>-port-<port-id>"
```

So `element.block(id: "b1", ports: (east: ((id: "out"),)))` exposes the
anchor `"b1-port-out"`. **Note the literal `-port-` infix** — it is *not*
a dot. Wires, stubs, and intersections all consume this anchor name as a
plain string.

Compass anchors `<id>.north / .east / .south / .west / .center` are also
exposed automatically, courtesy of CeTZ.

## Convention used in the rest of this folder

From here on, **only the body of the circuit block is shown** in inline
code samples — assume the same outer wrapper:

```typst
#import "@preview/circuiteria:0.2.0"
#circuiteria.circuit({
  import circuiteria: *
  // <snippet here>
})
```

Each `examples/<n>/<n>.typ` file in the reference folders is the *full,
compilable* version with the wrapper restored.

## Coordinates 30-second cheat sheet

Coordinates inside a `circuit({ ... })` body are CeTZ coordinates — the
same seven forms documented in
[`../../cetz/tutorial/03-coordinates.md`](../../cetz/tutorial/03-coordinates.md).
Most often you will use:

| Form | Example | Meaning |
| ---- | ------- | ------- |
| xyz tuple | `x: 0, y: 0` | Cartesian element origin (bottom-left) |
| Anchor string | `"b1-port-out"` | A port anchor created by an element |
| Compass anchor | `"b1.east"` | Border anchor on the named element |
| Relative `x:` dict | `x: (rel: 1, to: "g1.east")` | 1 unit right of `g1.east` |
| Relative `y:` dict | `y: (from: "b1-port-out", to: "in1")` | place this element so its `in1` port aligns with `b1-port-out` |

Up is positive y (CeTZ convention).

## Next steps

- [`../reference/circuit/01-circuit.md`](../reference/circuit/01-circuit.md) —
  the `circuit(...)` envelope: `body`, `length`.
- [`../reference/element/03-block.md`](../reference/element/03-block.md) —
  the most general element with arbitrary ports.
- [`../reference/wire/03-wire.md`](../reference/wire/03-wire.md) — connecting
  ports with `direct`, `zigzag`, or `dodge` wires.
- [`../reference/gates/00-gates-overview.md`](../reference/gates/00-gates-overview.md) —
  ready-made logic gates.
