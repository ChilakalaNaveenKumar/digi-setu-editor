# Demos — Nielsen-Chuang reproductions

Six famous circuits from *Quantum Computation and Quantum Information*
(Nielsen & Chuang, 2010), each as an isolated runnable `.typ`. These
mirror Section X of the Quill manual but are validated to compile
under Quill 0.7.2 + Typst 0.14.

| File | Figure | Manual section |
| ---- | ------ | -------------- |
| [`examples/01-teleportation/01-teleportation.typ`](examples/01-teleportation/01-teleportation.typ) | Quantum teleportation (Fig. 4.15) | X.a |
| [`examples/02-phase-estimation/02-phase-estimation.typ`](examples/02-phase-estimation/02-phase-estimation.typ) | Quantum phase estimation (Fig. 5.2) | X.b |
| [`examples/03-qft/03-qft.typ`](examples/03-qft/03-qft.typ) | Quantum Fourier transform (Fig. 5.1) | X.c |
| [`examples/04-shor-9/04-shor-9.typ`](examples/04-shor-9/04-shor-9.typ) | Shor 9-qubit code encoder (Fig. 10.4) | X.d |
| [`examples/05-fault-tolerant-meas/05-fault-tolerant-meas.typ`](examples/05-fault-tolerant-meas/05-fault-tolerant-meas.typ) | Fault-tolerant measurement (Fig. 10.28) | X.e |
| [`examples/06-fault-tolerant-pi8/06-fault-tolerant-pi8.typ`](examples/06-fault-tolerant-pi8/06-fault-tolerant-pi8.typ) | Fault-tolerant π/8 gate (Ex. 10.66) | X.f |

Run any of them with `typst compile <path>.typ` to get a clean PDF.
The pages below describe what each circuit demonstrates.

| Demo | Why it's interesting |
| ---- | -------------------- |
| Teleportation | The textbook example of `lstick` + control wires + measurement-conditioned classical gates. |
| Phase estimation | Heavy use of `setwire(0)`, manual `lstick` placement, `midstick(...)` for ellipses. |
| QFT | Many controlled rotations, `scale: 85%` to fit, ellipses across rows and columns. |
| Shor 9-qubit | Reusable ancilla pattern via `#let ancillas = (...)` + spread `..ancillas`. |
| Fault-tolerant meas | `gategroup` overlays labelling Prepare / Verify / Decode phases, mixed wire types. |
| Fault-tolerant π/8 | `gategroup(stroke: dotted)` annotations with shared style via `gategroup.with(...)`. |
