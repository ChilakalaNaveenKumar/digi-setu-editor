#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*highlight-clip: true (default)*
#codly(
  highlight-clip: true,
  highlights: ((line: 1, start: 0, end: 3, fill: orange),),
)
```py
print('hello')
```

*highlight-clip: false*
#codly(
  highlight-clip: false,
  highlights: ((line: 1, start: 0, end: 3, fill: orange),),
)
```py
print('hello')
```
