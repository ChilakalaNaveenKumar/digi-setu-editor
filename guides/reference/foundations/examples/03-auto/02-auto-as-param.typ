// Demonstrates: passing 'auto' to a parameter that supports it asks the
// function to pick a smart default. Common case: 'box(width: auto)' makes
// the box exactly as wide as its content (vs. an explicit length).

// Implicit auto (default for box width)
#box(stroke: 0.5pt, inset: 4pt)[short]

#v(0.5em)

// Explicit auto -- same effect, more readable
#box(stroke: 0.5pt, inset: 4pt, width: auto)[short]

#v(0.5em)

// Explicit length -- container is forced to a specific width
#box(stroke: 0.5pt, inset: 4pt, width: 6cm)[short content in a wide box]
