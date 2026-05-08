// 'underline(body, stroke: auto, offset: auto, extent: 0pt, evade: true,
//            background: false)' draws a line below text.
//
// Same parameter shape as 'overline' / 'strike'. Often combined with
// 'show link: underline' to underline all hyperlinks.

= Default

This is #underline[important].

= Custom stroke + offset

Take #underline(stroke: 1.5pt + red, offset: 2pt)[care]
of your spacing.

= 'extent' for tighter / wider lines

#align(center, underline(extent: 2pt)[Chapter 1])

= 'evade' (default true: skips descenders like p, q, y, g, j)

evade true:  This #underline(evade: true)[is great]. \
evade false: This #underline(evade: false)[is great].

= 'background' for highlighter-style effect

#set underline(stroke: (thickness: 1em, paint: maroon, cap: "round"))
#underline(background: true)[Stylized highlight feel] \
#underline(background: false)[Hidden by line]

= Common pattern: underline all hyperlinks

#show link: underline

Visit #link("https://typst.app")[the Typst homepage] for more.
