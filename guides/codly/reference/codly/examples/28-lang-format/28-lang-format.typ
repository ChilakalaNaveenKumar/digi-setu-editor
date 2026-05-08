#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Default formatter:*
```py
print('Hello, world!')
```

*Function mapping:*
#codly(lang-format: (_, _, _) => [No!])
```py
print('Hello, world!')
```

*Disabled (none):*
#codly(lang-format: none)
```py
print('Hello, world!')
```
