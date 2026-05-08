#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

// Making the footer bold and blue
#codly(
  footer: [Hello, world!],
  footer-transform: (x) => {
    set text(fill: blue)
    strong(x)
  },
)
```typ
Hello, world!
```
