#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Line number outside of the block:*
#codly(number-placement: "outside")
```py
print('Hello, world!')
print('Goodbye, world!')
```

*Line number inside of the block:*
#codly(number-placement: "inside")
```py
print('Hello, world!')
print('Goodbye, world!')
```
