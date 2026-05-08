# Gallery — every visual symbol

The gallery reproduces the gate-shape table from the Quill manual
(Section V), with one runnable `.typ` per symbol and an explanation
of which constructor produced it.

| File | Symbol | Constructor |
| ---- | ------ | ----------- |
| [`01-normal-gate.typ`](01-normal-gate.typ) | `H` | `gate($H$)` (or `$H$`) |
| [`02-round-gate.typ`](02-round-gate.typ) | `(X)` | `gate($X$, radius: 100%)` |
| [`03-d-shaped-gate.typ`](03-d-shaped-gate.typ) | `Y)` | `gate($Y$, radius: (right: 100%))` |
| [`04-meter.typ`](04-meter.typ) | meter | `meter()` |
| [`05-meter-label.typ`](05-meter-label.typ) | labelled meter | `meter(label: $|±〉$)` |
| [`06-phase.typ`](06-phase.typ) | `α`-dot | `phase($alpha$)` |
| [`07-control-filled.typ`](07-control-filled.typ) | `●` | `ctrl()` |
| [`08-control-open.typ`](08-control-open.typ) | `○` | `ctrl(open: true)` |
| [`09-target.typ`](09-target.typ) | ⊕ | `targ()` |
| [`10-swap.typ`](10-swap.typ) | × | `swap()` |
| [`11-permutation.typ`](11-permutation.typ) | crossings | `permute(2, 0, 1)` |
| [`12-multi-qubit.typ`](12-multi-qubit.typ) | tall `U` | `mqgate($U$, n: 3)` |
| [`13-lstick.typ`](13-lstick.typ) | `|ψ⟩` start | `lstick($|psi〉$)` |
| [`14-rstick.typ`](14-rstick.typ) | `|ψ⟩` end | `rstick($|psi〉$)` |
| [`15-multi-lstick.typ`](15-multi-lstick.typ) | `{ |ψ⟩` | `lstick($|psi〉$, n: 2)` |
| [`16-multi-rstick.typ`](16-multi-rstick.typ) | `]|ψ⟩` | `rstick($|psi〉$, n: 2, brace: "]")` |
| [`17-midstick.typ`](17-midstick.typ) | `yeah` | `midstick("yeah")` |
| [`18-nwire.typ`](18-nwire.typ) | `5/` | `nwire(5)` |
| [`19-controlled-z.typ`](19-controlled-z.typ) | dot+dot | `ctrl(1)` + `ctrl()` |
| [`20-controlled-x.typ`](20-controlled-x.typ) | dot+⊕ | `ctrl(1)` + `targ()` |
| [`21-swap-gate.typ`](21-swap-gate.typ) | ×+× | `swap(1)` + `swap()` |
| [`22-controlled-h.typ`](22-controlled-h.typ) | `H`+dot | `mqgate($H$, target: 1)` + `ctrl()` |
| [`23-vertical-wire.typ`](23-vertical-wire.typ) | plain | `ctrl(1, show-dot: false)` |
| [`24-meter-classical.typ`](24-meter-classical.typ) | meter→classical | `meter(target: 1)` + `ctrl()` |
| [`25-classical-wire.typ`](25-classical-wire.typ) | `=` | `setwire(2)` |
| [`26-styled-wire.typ`](26-styled-wire.typ) | green wire | `setwire(1, stroke: green)` |
| [`27-labels-around-gate.typ`](27-labels-around-gate.typ) | many labels | `gate($Q$, label: (...))` |
| [`28-gate-inputs-outputs.typ`](28-gate-inputs-outputs.typ) | `U` with `x`/`y` labels | `mqgate($U$, n: 3, inputs: ..., outputs: ...)` |

Each example is the smallest possible standalone `.typ` that produces
just the symbol — handy for copy-pasting into a real document.
