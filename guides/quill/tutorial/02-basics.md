# 2 — Basics: gates, wires, row breaks

A circuit is created by calling `quantum-circuit(..)` with a flat list
of children. Consecutive items are placed left-to-right on the current
wire and joined with a horizontal wire automatically.

## `gate(body)` shorthand

Inside `quantum-circuit`, you can pass a gate body **directly** without
wrapping it in `gate()`. These three are equivalent:

```typst
gate($H$)
$H$
[$H$]
```

The math environment is **not** entered for you, so use displaystyle
math (`$ U_1 $`, with spaces around the `$`) when you need bigger
typesetting (e.g., double subscripts).

## Empty cells with integers

A plain integer reserves *that many cells of just wire* (no gate). It
replaces the long chains of `&` + `\qw` you might have written in
`quantikz`.

```typst
#quantum-circuit(
  1, $H$, 4, meter()
)
```

`1, $H$, 4, meter()` reads as: one empty cell, a Hadamard, four empty
cells, a meter.

## Row breaks with `[\\ ]`

A new wire is started with the literal content `[\ ]` — a Typst content
block containing a backslash-space:

```typst
#quantum-circuit(
  1, $H$, ctrl(1), 1, [\ ],
  2, targ(), 1
)
```

The first wire has Hadamard then a control connecting down to the next
wire. The second wire shows a CNOT target on the wire below.

Use `ctrl(0)` (or just `ctrl()`) for a *control without a target wire*
— useful for CZ gates where both ends are dots.

See [`examples/02-basics/02-basics.typ`](examples/02-basics/02-basics.typ).

## Lengths between cells

Inserting a length between two items adds a horizontal gutter at that
column:

```typst
#quantum-circuit($X$, $Y$, 10pt, $Z$)
```

If multiple lengths land in the same column on different rows, the
**maximum** is used. After a `[\\ ]`, a length becomes a vertical gutter
between wires — useful when one wire's labels would otherwise collide.

## Next

Continue with [`03-multi-qubit-and-labels.md`](03-multi-qubit-and-labels.md)
for `mqgate`, `lstick`, `rstick`.
