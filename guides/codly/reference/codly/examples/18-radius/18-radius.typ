#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Default radius:*
```py
print('Hello, world!')
print('Hello, world!')
```

*Overriden radius:*
#codly(radius: 2em)
```py
print('Hello, world!')
print('Hello, world!')
```

*Zero radius:*
#codly(radius: 0pt)
```py
print('Hello, world!')
print('Hello, world!')
```
