# API Reference — Overview

> Source: <https://touying-typ.github.io/docs/reference>

This is a curated map of Touying's auto-generated API reference, derived
from the doc-comments in the source files
([touying-typ/touying/src](https://github.com/touying-typ/touying/tree/main/src)).

## Core modules

| File | Module | Purpose |
| ---- | ------ | ------- |
| [`core/01-configs.md`](./core/01-configs.md)       | `configs`    | `config-page`, `config-common`, `config-info`, `config-colors`, `config-methods`, `config-store`, plus `touying-set-config` / `touying-get-config`. |
| [`core/02-core.md`](./core/02-core.md)             | `core`       | `touying-slide`, `touying-slide-wrapper`, `touying-slides`, `touying-fn-wrapper`, `touying-reducer`, `touying-recall`, `touying-equation`, `touying-mitex`, `touying-raw`, `slide`, `pause`, `meanwhile`, `only`, `uncover`, `alternatives`, `appendix`, waypoint helpers, and the slide-splitting machinery. |
| [`core/03-components.md`](./core/03-components.md) | `components` | Layout helpers — `cell`, `progress-bar`, `progressive-outline`, `custom-progressive-outline`, `adaptive-columns`, `mini-slides`, `cols`, `lazy-v`, `lazy-h`, `lazy-layout`, `side-by-side`, `checkerboard`. |
| [`core/04-slides.md`](./core/04-slides.md)         | `slides`     | The `slide(...)` engine: parameter contract for all theme-defined `slide` functions. |
| [`core/05-utils.md`](./core/05-utils.md)           | `utils`      | Helpers — `slide-counter`, `last-slide-number`, `touying-progress`, `display-current-heading`, `display-current-short-heading`, `current-heading`, `display-info-date`, `fit-to-height`, `fit-to-width`, `methods`, `merge-dicts`, `call-or-display`, `update-alpha`, `semi-transparent-cover`, `cover-with-rect`, `alert-with-primary-color`, `section-relationship`, `page-args-from-aspect-ratio`, `short-heading`. |
| [`core/06-magic.md`](./core/06-magic.md)           | `magic`      | Show-rule helpers — `bibliography`, `bibliography-as-footnote`, `markup-text`, plus various Typst-element overrides. |
| [`core/07-pdfpc.md`](./core/07-pdfpc.md)           | `pdfpc`      | Functions for generating pdfpc presenter metadata — `config(...)`, `speaker-note(...)`, `pdfpc-file(here())`. |

## Themes

| File | Theme |
| ---- | ----- |
| [`themes/01-aqua.md`](./themes/01-aqua.md)             | `aqua` |
| [`themes/02-dewdrop.md`](./themes/02-dewdrop.md)       | `dewdrop` |
| [`themes/03-metropolis.md`](./themes/03-metropolis.md) | `metropolis` |
| [`themes/04-simple.md`](./themes/04-simple.md)         | `simple` |
| [`themes/05-stargazer.md`](./themes/05-stargazer.md)   | `stargazer` |
| [`themes/06-university.md`](./themes/06-university.md) | `university` |

For tutorial-level usage of each theme, see [`../themes/`](../themes/).
The reference pages here document the `<name>-theme` parameters, color
defaults, and the per-theme slide function family.

## How to read these pages

Every reference page follows the same pattern:

1. **Source** — link to the upstream doc.
2. **Overview** — what the module is for.
3. **Functions** — name + signature + parameters + notes.
4. **Cross-references** — pointers into the tutorial / theme docs.

When in doubt, search for the function name in the tutorial / theme /
integration docs first — the reference pages are deliberately terse and
assume you've already read the tutorial.
