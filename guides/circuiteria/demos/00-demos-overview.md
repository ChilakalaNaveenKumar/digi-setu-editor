# Circuiteria demos

Multi-section worked examples that combine many Circuiteria features
in a single document.

| File | Topic |
| ---- | ----- |
| [`examples/01-build-an-alu/01-build-an-alu.typ`](examples/01-build-an-alu/01-build-an-alu.typ) | Build an ALU step-by-step: half adder → full adder → 4-bit ripple-carry → add/sub unit. |
| [`examples/02-mips-datapath/02-mips-datapath.typ`](examples/02-mips-datapath/02-mips-datapath.typ) | MIPS-flavoured single-cycle datapath: PC, IMEM, register file, sign-extender, ALU, DMEM, write-back mux. |
| [`examples/03-memory-hierarchy/03-memory-hierarchy.typ`](examples/03-memory-hierarchy/03-memory-hierarchy.typ) | CPU core (grouped) → L1 → L2 → DRAM, with hit/miss arrows and per-level latency labels. |

Run any of them with:

```bash
typst compile demos/examples/02-mips-datapath/02-mips-datapath.typ out.pdf
```
