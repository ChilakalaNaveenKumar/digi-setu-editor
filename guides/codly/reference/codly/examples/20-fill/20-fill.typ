#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Default fill:*
```py
print('Hello, world!')
print('Hello, world!')
```

*Overriden fill (gradient):*
#codly(fill: gradient.linear(..color.map.flare))
```py
print('Hello, world!')
print('Hello, world!')
```

*No fill:*
#codly(fill: none)
```py
print('Hello, world!')
print('Hello, world!')
```
