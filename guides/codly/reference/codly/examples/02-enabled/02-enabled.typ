#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Enabled = true*:
#codly(enabled: true)
```typ
Hello, world!
```

*Enabled = false*:
#codly(enabled: false)
```typ
Hello, world!
```
