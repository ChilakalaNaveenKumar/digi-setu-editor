// 'bibliography(sources, title: ?, full: false, style: "ieee")' is the
// reference listing. The bibliography only lists works that were CITED
// somewhere in the document, unless 'full: true'.
//
// 'sources' can be:
//   - a path string to a Hayagriva (.yaml/.yml) or BibLaTeX (.bib) file
//   - raw bytes containing such a file
//   - an array of any of the above
//
// 'style' takes a built-in style name (string), a path to a CSL file, or
// raw bytes of CSL content. See the official docs for the full list of
// built-in styles. Common picks per discipline:
//
//   "ieee"                    Engineering, IT
//   "apa"                     Psychology, Life Sciences
//   "chicago-author-date"     Social sciences
//   "mla" / "chicago-notes"   Humanities
//   "american-physics-society" Physics

#bibliography("_assets/works.bib", style: "ieee", title: [References])

= Introduction

We summarize three sources here.

The pirate world has its own social structure @netwok. Distress signals
have been studied in detail @distress, including a famous early treatise
@arrgh.

A work that is NOT cited will only appear if 'full: true' is passed:
#cite(<tolkien54>, form: none) keeps it silent but enrolls it in the
bibliography listing.
