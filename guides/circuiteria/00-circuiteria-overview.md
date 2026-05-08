# Circuiteria — Block Circuit Diagrams for Typst

> **Circuiteria version:** 0.2.0
> **Source manual:** `guides/manual (2).pdf` (the full upstream PDF, 24 pages)
> **Built on:** [`cetz`](https://typst.app/universe/package/cetz)
> **Audience:** an LLM agent that authors `.typ` files using the
> [`circuiteria`](https://typst.app/universe/package/circuiteria) package. This
> sub-tree is the Circuiteria reference, organised the same way as the CeTZ
> reference under `../cetz/reference/`.

Circuiteria provides a way to make beautiful **block circuit diagrams** using
the CeTZ package as the underlying drawing layer. It ships ready-made
elements (blocks, ALUs, multiplexers, extenders, logic gates), a wire system
with multiple routing styles (direct / zigzag / dodge), automatic port
placement, and a small utility module of helpers (`lpad`, anchor rotation,
a colour palette).

## What this folder contains

| Folder | Contents |
| ------ | -------- |
| [`tutorial/`](./tutorial/) | Read-this-first concept material — installation, the `circuit` envelope, ports, anchors, wires. |
| [`reference/circuit/`](./reference/circuit/) | The single `circuit(...)` entry-point. |
| [`reference/util/`](./reference/util/) | Small helpers: `lpad`, `opposite-anchor`, `rotate-anchor`, plus the `colors` palette. |
| [`reference/wire/`](./reference/wire/) | Wire system: `wire`, `stub`, `intersection`, plus the `wire-styles` enum. |
| [`reference/element/`](./reference/element/) | Drawable circuit blocks: `elmt`, `alu`, `block`, `extender`, `multiplexer`, `group`. |
| [`reference/gates/`](./reference/gates/) | Logic gates: `gate`, `gate-and`, `gate-nand`, `gate-buf`, `gate-not`, `gate-or`, `gate-nor`, `gate-xor`, `gate-xnor`. |
| [`gallery/`](./gallery/) | 10 stand-alone showcase circuits (half/full adder, 4-bit ripple-carry, 2:1 / 4:1 muxes, 2-to-4 decoder, D flip-flop, 4-bit register, comparator, CPU datapath). |
| [`demos/`](./demos/) | 3 multi-section narratives: building an ALU, MIPS single-cycle datapath, memory hierarchy. |

## The 30-second tour

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

Three things to remember:

1. **Always import `circuiteria: *` *inside* the `circuit` block.** The
   sub-modules (`circuit.element`, `circuit.wire`, `circuit.util`,
   `circuit.gates`) are exported as top-level names (`element`, `wire`,
   `util`, `gates`) once you import the package contents.
2. **Ports follow a strict id convention.** A port declared on element
   `"alu"` with id `"in1"` becomes the anchor `"alu-port-in1"` (note the
   `-port-` infix). Connect wires and stubs to that exact name.
3. **Circuiteria is built on CeTZ.** All coordinates, anchors, strokes,
   colours, and helper functions you already know from CeTZ are still
   available — Circuiteria adds *block-shaped* elements on top. To call
   CeTZ primitives (`draw.circle`, `draw.line`, `draw.content`, …) inside
   the body, add an explicit `#import "@preview/cetz:0.3.2": draw` — the
   `draw` namespace is *not* re-exported by `import circuiteria: *`.

## How each reference page is structured

Every function `.md` follows the same shape (mirroring
`../cetz/reference/shapes/01-circle.md`):

1. **Summary** — one paragraph, what the function does.
2. **Signature** — fenced `text` block with the full positional + named
   parameter list and types from the upstream manual.
3. **Parameters** — a per-arg table or bullet list capturing the
   descriptions verbatim from the manual.
4. **Anchors / Ports** — what named anchors the element exposes
   (e.g. `<id>-port-<port-id>`, compass anchors, `<id>.center`).
5. **Pitfalls / cross-references** — agent-targeted notes (e.g. *"the
   anchor convention is `<id>-port-<port-id>`, with `-port-` between"*).
6. **Runnable example** — link to the `.typ` file in the sibling
   `examples/<NN-name>/` folder.

The `.typ` examples are kept short and *each one wraps the manual snippet
in a proper `#circuiteria.circuit({ import circuiteria: *; … })`* so you can
`typst compile` them as-is.

## Quick installation

Circuiteria lives on the Typst package registry (`@preview` namespace), so no
manual install is needed:

```typst
#import "@preview/circuiteria:0.2.0"
```

If you have the source vendored in your project, point the import at it
instead:

```typst
#import "src/lib.typ" as circuiteria
#circuiteria.circuit({
  import circuiteria: *
  // ...
})
```

The version this port targets is **0.2.0** (which itself depends on
`@preview/cetz:0.3.2` internally).

## Conceptual map (where to start)

| If you want to … | Read |
| ---------------- | ---- |
| Draw your first block diagram | [`tutorial/01-getting-started.md`](./tutorial/01-getting-started.md) |
| Set up the `circuit` envelope and the base unit (`length:`) | [`reference/circuit/01-circuit.md`](./reference/circuit/01-circuit.md) |
| Add ports to a block and reference them with `<id>-port-<port-id>` | [`reference/element/03-block.md`](./reference/element/03-block.md) |
| Connect blocks with wires (`direct`, `zigzag`, `dodge`) | [`reference/wire/03-wire.md`](./reference/wire/03-wire.md) |
| Stick a small wire end out of a port (open input/output) | [`reference/wire/02-stub.md`](./reference/wire/02-stub.md) |
| Draw an ALU, multiplexer, bit-extender | [`reference/element/02-alu.md`](./reference/element/02-alu.md), [`05-multiplexer.md`](./reference/element/05-multiplexer.md), [`04-extender.md`](./reference/element/04-extender.md) |
| Draw an AND / OR / NOT / NAND / NOR / XOR / XNOR / buffer gate | [`reference/gates/00-gates-overview.md`](./reference/gates/00-gates-overview.md) |
| Group elements together with a labelled border | [`reference/element/06-group.md`](./reference/element/06-group.md) |
| Use the predefined colour palette | [`reference/util/04-colors.md`](./reference/util/04-colors.md) |

## Notes on fidelity

- All function signatures, parameter names, parameter types, default values,
  port-anchor conventions, and styling defaults are taken verbatim from the
  upstream manual (`guides/manual (2).pdf`, Circuiteria v0.2.0).
- Where the manual's own example used `element.<fn>(...)`, `wire.<fn>(...)`,
  `gates.<fn>(...)`, or `util.<fn>(...)`, the example file does the same so
  it compiles without needing extra `import` statements beyond
  `import circuiteria: *`.
- Where the manual references CeTZ for coordinates, anchors, strokes, or
  colours, the cross-references point at the sibling `../cetz/...` folder
  in this guides tree.
