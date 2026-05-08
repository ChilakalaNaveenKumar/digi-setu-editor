// Multiple options demoed:
//   - 'style: "apa"' uses author-date inline citations
//   - 'full: true' lists ALL entries from the .bib file, even if uncited
//   - 'title: none' suppresses the bibliography heading
//
// To force the bibliography heading to be numbered, use a show-set rule:
//   #show bibliography: set heading(numbering: "1.")

#bibliography("_assets/works.bib", style: "apa", full: true, title: none)

= Pirates: an APA-style overview

We cite the social-structure work @netwok and the distress-signal study
@distress. Even though we don't cite the other entries, 'full: true' makes
them all show up below.

#pagebreak()

= Bibliography (no auto title; we drew our own)

(See the listing on the previous page; 'title: none' suppressed the
default heading.)
