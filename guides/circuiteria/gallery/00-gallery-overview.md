# Circuiteria gallery

Stand-alone, copy-pasteable digital circuits that show what
Circuiteria can do. Each `.typ` file compiles by itself.

| File | Diagram |
| ---- | ------- |
| [`01-half-adder.typ`](01-half-adder.typ) | Half adder from XOR + AND, with input fan-out junctions. |
| [`02-full-adder.typ`](02-full-adder.typ) | Full adder built from 2× XOR + 2× AND + OR with junctions for `A`, `B`, and `Cin`. |
| [`03-ripple-carry-4bit.typ`](03-ripple-carry-4bit.typ) | 4-bit ripple-carry adder — four labelled `block` FAs chained via the carry. |
| [`04-mux-2to1.typ`](04-mux-2to1.typ) | 2:1 multiplexer realised from gates: `Y = A·!S + B·S`. |
| [`05-mux-4to1.typ`](05-mux-4to1.typ) | 4:1 multiplexer using the high-level `multiplexer` element. |
| [`06-decoder-2to4.typ`](06-decoder-2to4.typ) | 2-to-4 decoder built from NOT + AND gates (the four minterms). |
| [`07-d-flipflop.typ`](07-d-flipflop.typ) | D flip-flop drawn as a labelled block with `clock` port, async clear, and complementary outputs. |
| [`08-register-4bit.typ`](08-register-4bit.typ) | 4-bit register (4× D-FFs sharing CLK and CLR buses with intersections). |
| [`09-comparator.typ`](09-comparator.typ) | 1-bit magnitude comparator (A>B, A=B, A<B) from gates. |
| [`10-cpu-datapath.typ`](10-cpu-datapath.typ) | Block-level CPU datapath: PC → I-MEM → Reg-File → ALU → D-MEM → write-back mux. |

Run any of them with:

```bash
typst compile gallery/03-ripple-carry-4bit.typ out.pdf
```
