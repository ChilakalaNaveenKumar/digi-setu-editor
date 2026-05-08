# `plugin` — load a WebAssembly module

> **No compile-verified example for this page.**
> Plugins require an external `.wasm` artifact, which we don't ship in this repo. The annotated snippets below are taken from the official docs and the `wasm-minimal-protocol` examples; treat them as syntax reference, not as runnable code. For working samples, see [wasm-minimal-protocol/examples](https://github.com/astrale-sharp/wasm-minimal-protocol/tree/master/examples) or any plugin-bearing package on Typst Universe (e.g. `oxifmt`, `cetz`).

## What it is

`plugin(source) -> module`

Loads a 32-bit WebAssembly module and returns a Typst `module`. Each WASM export becomes a callable Typst function. `source` is either:

- a path string (`"hello.wasm"`), resolved like any [Typst path](https://typst.app/docs/reference/syntax/#paths), or
- a `bytes` value containing the raw module.

## Calling shape

Every plugin function:

- takes 0..N `bytes` arguments,
- returns one `bytes` value (or signals an error).

So the idiomatic wrapper converts native Typst types to/from bytes around the call:

```typst
#let myplugin = plugin("hello.wasm")

#let concat(a, b) = str(
  myplugin.concatenate(bytes(a), bytes(b))
)

#concat("hello", "world")
```

You can also import named functions directly:

```typst
#import plugin("hello.wasm"): concatenate
```

## Purity requirement

Plugin functions **must be pure**: same arguments → same result, no observable side effects across calls. Typst will:

- cache calls by argument hash and skip re-execution,
- run multiple plugin instances on multiple threads with no shared state.

Calling an impure function via the normal call form yields **undefined, irreproducible** behavior. Typst does not enforce this — it's on you.

## Stateful plugins: the `transition` API

For plugins that need expensive runtime state (initialization, accumulators), use `plugin.transition`:

```typst
plugin.transition(func, ..arguments: bytes) -> module
```

It calls `func` once with `arguments`, then returns a **derived module** in which subsequent calls observe the side effects of that transition. The original module is unchanged.

```typst
#let base = plugin("hello-mut.wasm")
#assert.eq(base.get(), "[]")

#let mutated = plugin.transition(base.add, "hello")
#assert.eq(base.get(),    "[]")        // original untouched
#assert.eq(mutated.get(), "[hello]")   // derived sees the mutation
```

Caveat: the transition reflects changes in the plugin's memory, **not** in WebAssembly globals. If your plugin relies on global mutation, avoid `transition` for now.

## Protocol summary (for plugin authors)

A WASM module conforming to Typst's plugin protocol must:

- Export functions whose signatures are `(i32, i32, ..., i32) -> i32`. Each `i32` argument is the **length** of an input buffer.
- Allocate a buffer of size `sum(args)` and call the imported `wasm_minimal_protocol_write_args_to_buffer(ptr)` to receive concatenated argument bytes.
- Compute its result, then call the imported `wasm_minimal_protocol_send_result_to_host(ptr, len)` to return bytes to Typst.
- Return `0` for success, `1` for error (the result buffer is then interpreted as a UTF-8 error message).

Imports the host provides:

```
(import "typst_env" "wasm_minimal_protocol_write_args_to_buffer"
        (func (param i32)))
(import "typst_env" "wasm_minimal_protocol_send_result_to_host"
        (func (param i32 i32)))
```

## WASI is not supported

Plugins run in an isolated sandbox. Compilers that target WASI by default (emscripten, etc.) will not work — either retarget to plain `wasm32-unknown-unknown` or stub the WASI imports (e.g. with [wasi-stub](https://github.com/astrale-sharp/wasm-minimal-protocol/tree/master/crates/wasi-stub)).

## Pitfalls

- **All I/O is forbidden in the plugin sandbox** — no file reads, no printing, no network. Resource access happens on the Typst side.
- **Plugins are typically wrapped in a package** that exposes ergonomic functions and hides the bytes-shuffling. Authoring a plugin AND a wrapper package is the normal full path.
- **Argument order = byte buffer order.** Plugin authors must concatenate input args into a single buffer in the same order they appear in the Typst call.
- **Don't rely on order-of-call-side-effects** in pure mode. Cache hits will skip your function.

## Reference

- Official: https://typst.app/docs/reference/foundations/plugin/
- Protocol + examples: https://github.com/astrale-sharp/wasm-minimal-protocol
