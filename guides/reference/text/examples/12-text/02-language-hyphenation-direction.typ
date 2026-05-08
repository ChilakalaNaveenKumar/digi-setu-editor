// Group 2: LANGUAGE / SCRIPT / DIRECTION / HYPHENATION
//
//   lang      str    ISO 639-1/2/3 code (default "en")
//   region    str    ISO 3166-1 alpha-2 region (e.g. "GB", "US")
//   script    str    OpenType script tag (auto: per-block detection)
//   dir       auto | ltr | rtl   dominant direction (auto = inferred from lang)
//   hyphenate auto | bool        auto = enabled iff par.justify is on
//   costs     dict   tweaks the optimizer's preference for hyphenation,
//                      runt, widow, orphan (each as ratio of default; default 100%)
//
// Language affects: hyphenation patterns, smart quotes, smallcaps, digits,
// PDF/HTML accessibility metadata, and screen-reader voice.

= German with hyphenation

#set page(width: 220pt)
#set text(lang: "de")
#set par(justify: true)

Donaudampfschifffahrtsgesellschaftskapitän erfreut sich
großer Beliebtheit unter Schüler:innen.

= Right-to-left (Arabic)

#set text(lang: "ar", dir: rtl)
هذا نص عربي مكتوب من اليمين إلى اليسار.

#set text(lang: "en", dir: ltr)

= Costs: discourage hyphenation

#set page(width: 220pt)
#set par(justify: true)
#set text(hyphenate: true, lang: "en")

Default hyphenation cost (100%):

#lorem(15)

10x cost makes the optimizer hyphenate much less often:

#set text(costs: (hyphenation: 1000%))
#lorem(15)

#set text(costs: (hyphenation: 100%))

= region affects locale-aware behaviour

#set text(lang: "en", region: "GB")
British English region.

#set text(lang: "en", region: "US")
US English region.
