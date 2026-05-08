#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Enabled codly*
```typ
= Example
*Hello, World!*
```

*Disabled codly*
#no-codly[
  ```typ
  = Example
  *Hello, World!*
  ```
]
