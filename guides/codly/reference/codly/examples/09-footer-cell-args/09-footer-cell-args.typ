#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

// Centering the footer
#codly(
  footer: [*Hello, world!*],
  footer-cell-args: (align: center,),
)
```typ
Hello, world!
```
