// Demonstrates: markup is syntactic sugar for function calls.
// '= Title' is exactly equivalent to '#heading[Title]'.
// Likewise '+ item' is '#enum[item]', '- item' is '#list[item]', etc.
// This is why 'set heading(...)' affects '= ...' headings.

= Implicit Heading

#heading[Explicit Heading]

#heading(level: 2)[Explicit Level-Two Heading]

== Implicit Level-Two Heading
