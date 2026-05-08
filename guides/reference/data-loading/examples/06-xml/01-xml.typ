#set page(width: 14cm, height: auto, margin: 1cm)

#let find-child(elem, tag) = elem.children.find(
  e => type(e) == dictionary and e.tag == tag,
)
#let text-of(elem) = elem.children.first()

#let render-article(art) = {
  let title = find-child(art, "title")
  let author = find-child(art, "author")
  let content = find-child(art, "content")

  [
    = #text-of(title)
    _by #text-of(author)_

    #for p in content.children {
      if type(p) == dictionary and p.tag == "p" {
        parbreak()
        text-of(p)
      }
    }
  ]
}

#let root = xml("_assets/news.xml").first()
#for child in root.children {
  if type(child) == dictionary and child.tag == "article" {
    render-article(child)
    v(0.5em)
  }
}
