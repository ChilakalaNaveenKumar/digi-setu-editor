#set page(width: 12cm, height: 8cm, margin: 1cm, numbering: "(i)")

= Preface
Some preface text.

#pagebreak()
#set page(numbering: "1")
#counter(page).update(1)

= Chapter 1 <ch1>
Body of chapter 1.

#pagebreak()

= Chapter 2 <ch2>
Body of chapter 2.

#pagebreak()

#context [
  *Reading locations* \
  Chapter 1 physical page: #locate(<ch1>).page() \
  Chapter 1 position:      #repr(locate(<ch1>).position()) \
  Chapter 1 displayed:     #numbering(
    locate(<ch1>).page-numbering(),
    ..counter(page).at(locate(<ch1>)),
  ) \
  Chapter 2 displayed:     #numbering(
    locate(<ch2>).page-numbering(),
    ..counter(page).at(locate(<ch2>)),
  )
]
