# Fletcher gallery

Stand-alone, copy-pasteable diagrams that show what Fletcher is good
at. Each `.typ` file compiles by itself — open one in the playground
and tweak.

| File | Diagram |
| ---- | ------- |
| [`01-commutative-square.typ`](01-commutative-square.typ) | Commutative square `A → B → D ← C ← A` plus the diagonal composite. |
| [`02-pullback.typ`](02-pullback.typ) | Pullback `P` of `X → Z ← Y` with the right-angle marker drawn via a CeTZ overlay. |
| [`03-snake-lemma.typ`](03-snake-lemma.typ) | The snake lemma — kernels and cokernels with the serpentine connecting morphism `δ`. |
| [`04-finite-automaton.typ`](04-finite-automaton.typ) | DFA recognising binary strings ending in `01`, with self-loops and an accepting (double-circle) state. |
| [`05-feedforward-nn.typ`](05-feedforward-nn.typ) | Fully-connected MLP (4 → 5 → 3) with semi-transparent edges. |
| [`06-divisibility-lattice.typ`](06-divisibility-lattice.typ) | Hasse diagram of the divisors of 60 ordered by divisibility. |
| [`07-pipeline.typ`](07-pipeline.typ) | CI/CD pipeline with parallel build branches and a "revert on failure" feedback edge. |
| [`08-er-diagram.typ`](08-er-diagram.typ) | Entity-relationship diagram (Customer–Order–Product) with cardinality labels and attribute ovals. |
| [`09-state-machine.typ`](09-state-machine.typ) | Order lifecycle FSM with happy-path arrows and a "cancel from anywhere" branch. |
| [`10-yoneda.typ`](10-yoneda.typ) | Naturality square for `Hom(-, -)` with a curved diagonal. |
| [`11-bezier-overlay.typ`](11-bezier-overlay.typ) | Custom Bezier edge drawn via `render:` + `cetz.draw.bezier`. |
| [`12-grouped-enclose.typ`](12-grouped-enclose.typ) | OS-style architecture diagram with three `enclose:`-grouped layers (apps / kernel services / drivers). |

## Why these

Each example targets a *concrete pattern* people actually draw:
category theory, automata, neural nets, lattices, software pipelines,
ER diagrams, state machines. None of them are "two letters and an
arrow" — they're meant as starting templates.

## Running them

```bash
typst compile gallery/04-finite-automaton.typ out.pdf
```

Or import the file inline from a containing document:

```typst
#include "gallery/04-finite-automaton.typ"
```
