// Attaches a CSV next to the PDF. Open the resulting PDF in a reader
// that supports attachments (e.g. Adobe Acrobat) to see "notes.csv"
// in the sidebar.

#pdf.attach(
  "_assets/notes.csv",
  relationship: "supplement",
  mime-type: "text/csv",
  description: "Raw experimental readings from the Arctic study",
)

= Document with a CSV attachment

This document is intentionally short. Open it in a PDF reader and
look at the attachments / "Files" panel — you should see
`notes.csv` listed.

#pad(top: 1em)[
  *Description provided in the PDF:* Raw experimental readings from
  the Arctic study.
]
