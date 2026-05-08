// Compile with HTML export to see the inline SVG:
//   typst compile --features html --format html 01-frame.typ 01-frame.html

= Article with an embedded diagram

In HTML, semantic content (headings, paragraphs, lists) becomes real
HTML. The diagram below is rendered with Typst's layout engine and
embedded as inline SVG so it looks identical in HTML and PDF.

#figure(
  html.frame(
    rect(
      width: 6cm, height: 4cm, fill: aqua.lighten(70%),
      align(center + horizon)[
        #stack(spacing: 8pt,
          text(weight: "bold", size: 14pt)[Customer],
          [arrow → Product])
      ],
    ),
  ),
  caption: [Customer journey overview.],
  alt: "Diagram with a labelled box pointing from Customer to Product.",
)

The rest of this paragraph is rendered as semantic HTML (`<p>`),
selectable, and reflowable on a phone.
