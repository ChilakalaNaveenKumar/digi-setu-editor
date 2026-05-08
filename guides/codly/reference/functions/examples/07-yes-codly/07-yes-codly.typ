#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Disabled codly*
#codly(enabled: false)
```typ
= Example
*Hello, World!*
```

*Enabled codly*
#yes-codly[
  ```typ
  = Example
  *Hello, World!*
  ```
]
