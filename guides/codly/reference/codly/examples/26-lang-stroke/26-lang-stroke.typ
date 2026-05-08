#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Fixed stroke:*
#codly(lang-stroke: 1pt + red)
```py
print('Hello, world!')
print('Goodbye, world!')
```

*Function mapping:*
#codly(lang-stroke: (lang) => 2pt + lang.color)
```py
print('Hello, world!')
print('Goodbye, world!')
```
