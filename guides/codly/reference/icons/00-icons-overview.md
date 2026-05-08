# Icons — Overview

Section 4 of the manual: how to wire up *nice icons* (Tabler / Font
Awesome / Material Icons / etc.) for language pills, plus the single
built-in icon helper for the Typst language.

| Function | Purpose | Page |
| -------- | ------- | ---- |
| `typst-icon` | Built-in language definition for the Typst language. Spread into your `languages:` dictionary. | [`01-typst-icon.md`](./01-typst-icon.md) |

## Step-by-step recipe (from the manual)

1. **Choose an icon font.** Good options:
   - [Tabler Icons](https://tabler-icons.io)
   - [Font Awesome](https://fontawesome.com)
   - [Material Icons](https://fonts.google.com/icons)
   - Anything else from Google Fonts that exposes its glyphs at known
     unicode code-points.

2. **Download the font and put it in your project.** If using the Typst
   CLI, pass `--font <path>` so the compiler can find it.

3. **Use the icon's font selector** to find the unicode value of the
   glyph you want. For Tabler's `language` icon that is `ebbe`.

4. **Wrap it in a `text(...)`** and pass it as the `icon:` field of a
   language entry:

   ```typst
   #let icon = text(font: "tabler-icons", size: 1em, "\u{ebbe}")
   #codly(languages: (text: (icon: icon, name: "Text")))
   ```py
   Hello, world!
   ```
   ```

5. **Fix the baseline.** Tabler glyphs sit slightly too high; the
   manual recommends:

   ```typst
   #let icon = text(font: "tabler-icons", size: 1em, "\u{ebbe}", baseline: 0.1em)
   ```

6. **Spread the dictionary into your existing `languages:`** if you
   already use [`@preview/codly-languages`](https://typst.app/universe/package/codly-languages):

   ```typst
   #import "@preview/codly-languages:0.1.7": *
   #codly(languages: (..codly-languages, py: (icon: my-py-icon, name: "Python", color: green)))
   ```

## Pitfalls

- **The icon font must actually be installed** for `text(font: "...")`
  to find it. Otherwise Typst silently falls back to a tofu glyph (□).
- The `baseline:` trick is font-specific; tweak it per font if needed.
- `icon:` accepts arbitrary content — emoji, SVG via `image(...)`, or a
  `text(...)`-wrapped glyph all work.
