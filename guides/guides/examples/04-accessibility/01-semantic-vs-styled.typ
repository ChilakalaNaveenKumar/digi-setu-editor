#set page(width: 14cm, height: auto, margin: 1cm)
#set text(lang: "en")
#set document(title: "Accessibility demo")

== ❌ Looks like a heading, but isn't tagged as one

#text(size: 16pt, weight: "bold")[Heading]

This text is preceded by something that looks like a heading but
will not be announced as a heading by AT.

== ✅ Real heading (semantic)

#show heading: set text(size: 16pt)
= Heading

This is preceded by a real heading element.

== Restyling strong while keeping semantics

#show strong: set text(tracking: 0.2em, fill: blue, weight: "black")

When setting up your tents, *never forget* to secure the pegs.

== Lists, not raw bullets

- First item
- Second item
- Third item
