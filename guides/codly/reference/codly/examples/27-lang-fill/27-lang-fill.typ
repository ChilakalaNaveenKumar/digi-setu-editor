#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Fixed fill:*
#codly(lang-fill: red)
```py
print('Hello, world!')
print('Goodbye, world!')
```

*Function mapping:*
#codly(lang-fill: (lang) => lang.color.lighten(40%))
```py
print('Hello, world!')
print('Goodbye, world!')
```
