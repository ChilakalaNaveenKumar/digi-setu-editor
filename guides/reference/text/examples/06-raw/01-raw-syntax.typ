// 'raw(text, block: false, lang: none, align: start, syntaxes: (), theme: auto, tab-size: 2)'
// renders text verbatim in a monospace font.
//
// MARKUP SHORTHAND:
//   `inline`              -> raw inline (block: false), no language
//   ```                   -> raw block (block: true) starts/ends with 3+ backticks
//   ```rust   ... ```     -> raw block with language tag for syntax highlighting
//
//   ` ` (two backticks)   -> empty raw text
//
// You can use 4 or more backticks if your content needs to contain triple
// backticks; the closing fence must use the same count.
//
// Inside raw blocks, NOTHING is interpreted: no escapes, no markup, no math.
// The ONLY exception is the language tag immediately after opening backticks.

= Inline raw

Adding `rbx` to `rcx` gives the desired result. Inline raw uses single
backticks and inherits a smaller font size by default.

= Block raw, no highlighting

```
let plain = "no language tag, no highlighting"
{ key: 1, list: [a, b] }
```

= Block raw with language tag (syntax highlighting)

```rust
fn main() {
    let greeting = "Hello, World!";
    println!("{}", greeting);
}
```

```python
def factorial(n):
    return 1 if n <= 1 else n * factorial(n - 1)
```

= Special: raw containing backticks

This raw block contains ` `backticks` ` (the spaces around them are trimmed):

``` `inside backticks` ```

= Programmatic construction

You can also call 'raw(...)' directly:

#raw("fn " + "main() {}", lang: "rust")
