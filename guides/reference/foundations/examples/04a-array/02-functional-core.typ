#set page(width: 14cm, height: auto, margin: 1cm)

== map / filter / fold / reduce / sum / product

#let xs = (1, 2, 3, 4, 5)

map(square):   #xs.map(x => x * x) \
filter(even):  #xs.filter(calc.even) \
fold(+):       #xs.fold(0, (a, b) => a + b) \
reduce(max):   #xs.reduce((acc, x) => calc.max(acc, x)) \
sum:           #xs.sum() \
product:       #xs.product()

== any / all

any negative: #xs.any(x => x < 0) \
all positive: #xs.all(x => x > 0)

== Sorting (key, multi-criteria, custom comparator)

#("ant", "bee", "cat", "dog").sorted()
#("ant", "bee", "cat", "dog").sorted(key: w => w.len(),
                                     by: (l, r) => l >= r)
#((p: 2, n: "b"), (p: 1, n: "c"), (p: 2, n: "a")).sorted(
  key: it => (it.p, it.n))

== Joining, interspersing, flattening

#("Alice", "Bob", "Charlie").join(", ", last: ", and ") \
#("A", "B", "C").intersperse("-") \
#(1, (2, (3, 4))).flatten()

== Slicing, chunking, windowing

#xs.slice(1, 4) \
#xs.chunks(2) \
#xs.chunks(2, exact: true) \
#xs.windows(3) \
#(1, 1, 2, 3, 2, 4).split(2)

== enumerate / zip / range / to-dict

#for (i, c) in ("A", "B", "C").enumerate() [#i: #c \ ]

#(1, 2).zip((10, 20), (100, 200)) \
#range(2, 10, step: 3) \
#(("apples", 2), ("peaches", 3)).to-dict()
