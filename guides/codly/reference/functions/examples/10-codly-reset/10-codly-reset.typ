#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Global state with red color*
#codly(fill: red)
```typ
= Example
*Hello, World!*
```

*Reset it*
#codly-reset()
```typ
= Example
*Hello, World!*
```
