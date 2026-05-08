// Default raw uses 'DejaVu Sans Mono' at 0.8em (80% of normal size).
// Override with show-set rules.
//
// You can also custom-render whole blocks with show rules on raw or
// raw.where(...) to add boxes, padding, fills.

// Switch font + reset block size to match normal text.
#show raw: set text(font: "DejaVu Sans Mono", size: 0.85em)
#show raw.where(block: true): set text(1em / 0.85)

// Inline raw: small box with subtle fill.
#show raw.where(block: false): box.with(
  fill: luma(240),
  inset: (x: 3pt, y: 0pt),
  outset: (y: 3pt),
  radius: 2pt,
)

// Block raw: indented block with rounded fill.
#show raw.where(block: true): block.with(
  fill: luma(245),
  inset: 10pt,
  radius: 4pt,
)

= Inline raw is now boxed

Use `rg` to search recursively. Run `cargo build --release` for production
binaries.

= Block raw is now padded with rounded corners

```bash
rg "Hello World" /var/log
find . -name "*.txt" -mtime -7
```

```python
class TreeNode:
    def __init__(self, value):
        self.value = value
        self.children = []
```

= 'lang' tags include Typst itself

```typ
This is *Typst markup* with #emph[emphasis].
```

```typc
let f(x) = x + 1
let result = f(5)
```

```typm
sum_(i=1)^n i = n(n+1)/2
```
