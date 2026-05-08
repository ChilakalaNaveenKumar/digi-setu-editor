# Fletcher demos

Multi-section worked examples — these are full-page narratives with
several diagrams that go together.

| File | Topic |
| ---- | ----- |
| [`examples/01-category-theory/01-category-theory.typ`](examples/01-category-theory/01-category-theory.typ) | Identity, composition, isomorphism, and a 3-D cube of arrows. |
| [`examples/02-control-flow-graph/02-control-flow-graph.typ`](examples/02-control-flow-graph/02-control-flow-graph.typ) | A `while`-loop CFG with a back-edge, plus its dominator tree. |
| [`examples/03-tensor-network/03-tensor-network.typ`](examples/03-tensor-network/03-tensor-network.typ) | Penrose-style tensor network with open and contracted indices. |
| [`examples/04-tikz-translation/04-tikz-translation.typ`](examples/04-tikz-translation/04-tikz-translation.typ) | Three classic `tikz-cd` snippets re-implemented in Fletcher. |

Run any of them with:

```bash
typst compile demos/examples/01-category-theory/01-category-theory.typ out.pdf
```
