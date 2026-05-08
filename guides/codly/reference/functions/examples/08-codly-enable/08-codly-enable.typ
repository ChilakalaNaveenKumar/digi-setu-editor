#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Disabled codly*
#codly-disable()
```typ
= Example
*Hello, World!*
```

#codly-enable()

*Enabled codly*
```typ
= Example
*Hello, World!*
```
