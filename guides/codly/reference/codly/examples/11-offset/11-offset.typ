#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*No offset:*
```typ
Hello, world!
```

*Offset by 5:*
#codly(offset: 5)
```typ
Hello, world!
```
