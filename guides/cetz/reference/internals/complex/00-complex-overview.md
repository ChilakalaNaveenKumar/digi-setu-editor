# `complex` — Complex Number Arithmetic

A complex number `V` is represented as a 2-element tuple/vector `(re, im)`.
All functions accept and return that representation.

> **Internal module — not re-exported.** `cetz.complex.*` is *not* reachable
> via `cetz.<x>` from outside the package. The upstream manual documents
> these as "Internals" because they live in `cetz/src/complex.typ` and are
> used internally by other CeTZ modules. To call them from your own code
> you would have to vendor `cetz/src/complex.typ` into your project. The
> `.typ` examples in this folder therefore show the *equivalent computation
> in plain Typst* rather than calling `cetz.complex.<fn>` directly.

| Function | Page |
| -------- | ---- |
| `re(V)` | [`01-re.md`](./01-re.md) |
| `im(V)` | [`02-im.md`](./02-im.md) |
| `mul(V, W)` | [`03-mul.md`](./03-mul.md) |
| `conj(V)` | [`04-conj.md`](./04-conj.md) |
| `dot(V, W)` | [`05-dot.md`](./05-dot.md) |
| `normsq(V)` | [`06-normsq.md`](./06-normsq.md) |
| `norm(V)` | [`07-norm.md`](./07-norm.md) |
| `scale(V, t)` | [`08-scale.md`](./08-scale.md) |
| `unit(V)` | [`09-unit.md`](./09-unit.md) |
| `inv(V)` | [`10-inv.md`](./10-inv.md) |
| `div(V, W)` | [`11-div.md`](./11-div.md) |
| `add(V, W)` | [`12-add.md`](./12-add.md) |
| `sub(V, W)` | [`13-sub.md`](./13-sub.md) |
| `arg(V)` | [`14-arg.md`](./14-arg.md) |
| `ang(V, W)` | [`15-ang.md`](./15-ang.md) |
