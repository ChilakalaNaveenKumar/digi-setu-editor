#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Default stroke:*
```py
print('Hello, world!')
```

*No stroke:*
#codly(stroke: none)
```py
print('Hello, world!')
```

*Overriden stroke:*
#codly(stroke: 1pt + blue)
```py
print('Hello, world!')
```
