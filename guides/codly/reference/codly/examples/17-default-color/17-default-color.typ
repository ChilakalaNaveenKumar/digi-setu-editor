#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Default color:*
```py
print('Hello, world!')
print('Hello, world!')
```

*Overriden default color:*
#codly(default-color: orange)
```py
print('Hello, world!')
print('Hello, world!')
```
