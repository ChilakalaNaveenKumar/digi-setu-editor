// Compile with HTML export to see the typed elements:
//   typst compile --features html --format html 01-typed.typ 01-typed.html

#context if target() == "html" {
  html.nav(aria-label: "Site navigation", [
    #html.ul([
      #html.li([#link("/")[Home]])
      #html.li([#link("/blog/")[Blog]])
      #html.li([#link("/about/")[About]])
    ])
  ])

  html.section(class: "intro", [
    #html.h2[Welcome]
    #html.p[This entire section is built with typed HTML wrappers.]
  ])

  html.video(controls: true, width: 640, height: 360, [
    #html.source(src: "talk.webm", type: "video/webm")
    #html.source(src: "talk.mp4",  type: "video/mp4")
    #html.p[
      Your browser does not support video.
      #link("talk.mp4")[Download the file]
      instead.
    ]
  ])
} else [
  This example is intended for HTML export. In PDF/SVG/PNG output it
  doesn't render anything visible — see the .typ source for the
  HTML-only structure.
]
