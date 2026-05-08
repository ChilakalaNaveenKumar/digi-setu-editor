#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *

== Without `codly-init` — codly is silent

#codly(zebra-fill: aqua)
```py
print("This block is rendered as plain Typst raw — no Codly look.")
```

== After `#show: codly-init`

#show: codly-init

#codly(zebra-fill: aqua)
```py
print("Now the show rule is active and Codly takes over.")
```
