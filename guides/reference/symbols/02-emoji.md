# `emoji` — named emoji glyphs

Module of named emoji. Use `#emoji.<name>` (with optional dot-modifiers) anywhere in markup or code.

```typst
#emoji.face.cry          // 😢
#emoji.heart             // ❤  (plain 'heart' IS the red heart)
#emoji.heart.blue        // 💙
#emoji.cat               // 🐈
#emoji.party             // 🎉  (plain 'party' is the party popper)
```

## Naming conventions

| Pattern              | Meaning                                |
| -------------------- | -------------------------------------- |
| `face.<mood>`         | facial expressions: `face.smile`, `face.cry`, `face.angry`, `face.kiss`, `face.cool`, `face.think`, `face.smirk`, `face.tongue`, ... |
| `heart.<color>`       | hearts: `heart` (red, default), `heart.blue`, `heart.green`, `heart.purple`, `heart.pink`, `heart.broken`, `heart.beat`, ... |
| `hand.<gesture>`      | `hand.ok`, `hand.peace`, `hand.r`, `hand.l`, `hand.wave`, `hand.rock`, `hand.raised`, ... |
| `<animal>`            | `cat`, `dog`, `lion`, `unicorn`, `tiger`, `elephant`, ... |
| `<drink>`             | `coffee`, `cup.straw`, `beer`, ... |

> **Names are not always intuitive.** The default red heart is `heart`, not `heart.red`. The party popper is `party`, not `party.popper`. The thinking face is `face.think`, not `face.thinking`. **When in doubt, browse the official list** (linked below) — it's huge but searchable with Ctrl/Cmd-F.

The `sym` module's general modifiers (`.l`/`.r`, `.heavy`, etc.) often appear here too.

## Font requirement

Emoji glyphs need an emoji font installed. Without one you'll see "tofu" boxes (`▯`).

| OS       | Default emoji font            |
| -------- | ----------------------------- |
| macOS    | Apple Color Emoji             |
| Windows  | Segoe UI Emoji                |
| Linux    | Noto Color Emoji (when available) |

Typst also ships with a fallback emoji font in some distributions, but quality varies.

To force a specific emoji font:

```typst
#set text(font: ("Your Body Font", "Noto Color Emoji"))
```

The fallback list lets non-emoji glyphs come from your body font and emoji glyphs from the emoji font.

## Discovering emoji names

Browse the official searchable list at https://typst.app/docs/reference/symbols/emoji/. The list is huge — use Ctrl/Cmd-F.

## Inserting raw emoji characters

You can always paste a literal emoji character into your source. Named access is just an alternative when typing the character isn't easy.

```typst
A celebration 🎉 also works.
```

## Examples (compile-verified)

- `examples/02-emoji/01-emoji.typ` — faces, hearts, animals, hands, inline use in text.

## Reference

https://typst.app/docs/reference/symbols/emoji/
