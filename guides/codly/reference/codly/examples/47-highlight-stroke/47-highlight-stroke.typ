#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

#codly(
  highlight-stroke: (color) => 1pt + color,
  highlights: ((line: 1, start: 0, end: 5, fill: red),),
)
```py
print('hello world')
```
