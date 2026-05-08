// 'colbreak()' forces the next content into the next column.
// In a single-column layout (or the LAST column on a page) it acts like
// a page break.

#set page(columns: 2, height: 200pt)

Preliminary findings from our ongoing research project have revealed a
hitherto unknown phenomenon of extraordinary significance.

#colbreak()

Through rigorous experimentation and analysis, we have discovered a
hitherto uncharacterized process that defies our current understanding
of the fundamental laws of nature.

#colbreak(weak: true)
// 'weak: true' means: skip the break if we're already at the start of
// a new column. Useful inside templates that may or may not be already
// at a fresh column.
