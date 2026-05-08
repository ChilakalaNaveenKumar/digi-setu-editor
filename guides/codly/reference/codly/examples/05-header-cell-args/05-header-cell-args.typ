#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

// Centering the header
#codly(
  header: [*Hello, world!*],
  header-cell-args: (align: center,),
)
```typ
Hello, world!
```
