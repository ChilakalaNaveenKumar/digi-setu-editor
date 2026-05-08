#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

== Single length
*Default inset:*
```py
print('Hello, world!')
```

*Overriden inset:*
#codly(inset: 1em)
```py
print('Hello, world!')
```

== Dictionary inset
*Custom (x, y):*
#codly(inset: (x: 0.32em, y: 0.1em))
```py
print('Hello, world!')
```
