#set page(width: 10cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Enabled (default):*
```py
def quicksort(L):
    qsort = lambda L: [] if L==[] else qsort([x for x in L[1:] if x< L[0]]) + L[0:1] + qsort([x for x in L[1:] if x>=L[0]])
    qsort(L)
```

*Disabled:*
#codly(smart-indent: false)
```py
def quicksort(L):
    qsort = lambda L: [] if L==[] else qsort([x for x in L[1:] if x< L[0]]) + L[0:1] + qsort([x for x in L[1:] if x>=L[0]])
    qsort(L)
```
