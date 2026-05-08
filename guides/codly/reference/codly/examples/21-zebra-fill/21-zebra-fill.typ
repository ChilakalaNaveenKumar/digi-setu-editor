#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Default zebra:*
```py
print('Hello, world!')
print('Hello, world!')
```

*No zebra:*
#codly(zebra-fill: none)
```py
print('Hello, world!')
print('Hello, world!')
```

*Overriden zebra (gradient):*
#codly(zebra-fill: gradient.linear(..color.map.flare))
```py
print('Hello, world!')
print('Hello, world!')
```
