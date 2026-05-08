#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

#codly(
  display-name: false,
  languages: (
    py: (name: [Python], color: green, icon: "🐍"),
  ),
)
```py
print('Hello, world!')
print('Goodbye, world!')
```
