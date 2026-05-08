#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

// Making the header bold and blue
#codly(
  header: [Hello, world!],
  header-transform: (x) => {
    set text(fill: blue)
    strong(x)
  },
)
```typ
Hello, world!
```
