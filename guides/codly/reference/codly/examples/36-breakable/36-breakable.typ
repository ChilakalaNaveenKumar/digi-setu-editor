#set page(width: 14cm, height: 6cm, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Default (breakable: true) — block can split across pages.*
#codly(breakable: true)
```py
def long():
    print("line 1")
    print("line 2")
    print("line 3")
    print("line 4")
    print("line 5")
    print("line 6")
    print("line 7")
    print("line 8")
    print("line 9")
    print("line 10")
    print("line 11")
    print("line 12")
    print("line 13")
    print("line 14")
    print("line 15")
    print("line 16")
```

*With breakable: false — block is pushed whole to the next page.*
#codly(breakable: false)
```py
def short():
    print("line 1")
    print("line 2")
    print("line 3")
```
