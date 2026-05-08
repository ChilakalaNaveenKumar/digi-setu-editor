#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

#codly(header: [*Hello, world!*])
```typ
Hello, world!
```

// header has reset itself; this block has no header
```typ
Hello again, world!
```
