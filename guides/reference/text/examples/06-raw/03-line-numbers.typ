// 'raw.line' is a synthetic per-line element produced inside raw blocks.
// You can target it with show rules to add line numbers, alternating
// backgrounds, or any custom layout.
//
// Fields on raw.line:
//   it.number   line number, starts at 1
//   it.count    total number of lines in this raw block
//   it.text     the raw text of this line (no highlighting)
//   it.body     the highlighted content for this line

#show raw.line: it => box(
  width: 100%,
  inset: (x: 4pt, y: 0pt),
  grid(
    columns: (auto, 1fr),
    column-gutter: 8pt,
    align: (right + horizon, left + horizon),
    text(fill: gray, size: 0.85em)[#it.number],
    it.body,
  ),
)

// Block raw with a subtle background to show the per-line layout.
#show raw.where(block: true): block.with(
  fill: luma(248),
  stroke: 0.4pt + luma(220),
  radius: 4pt,
  inset: 8pt,
  width: 100%,
)

= Line-numbered code

```python
def quicksort(items):
    if len(items) <= 1:
        return items
    pivot = items[0]
    rest = items[1:]
    lo = [x for x in rest if x <= pivot]
    hi = [x for x in rest if x > pivot]
    return quicksort(lo) + [pivot] + quicksort(hi)
```

= Inline raw is unaffected

The `quicksort` function above runs in `O(n log n)` average time.
