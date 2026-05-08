# External — Gistd

> Source: <https://touying-typ.github.io/docs/external/gistd>
>
> Service: <https://gistd.myriad-dreamin.com/>

[Gistd](https://github.com/Myriad-Dreamin/gistd) is a browser-based
Typst-document viewer. It compiles Typst on the client (via
[typst.ts](https://github.com/Myriad-Dreamin/typst.ts)), so unlike static
PDF / PNG exports you can **select and copy text** in the rendered
output.

- Global (Cloudflare CDN): <https://gistd.myriad-dreamin.com/>
- Asia mirror: <https://gistd-cn.myriad-dreamin.com/>

## Loading a GitHub document

Replace `github.com` with `gistd.myriad-dreamin.com` in the GitHub URL:

```
GitHub : https://github.com/typst/templates/blob/main/charged-ieee/template/main.typ
Gistd  : https://gistd.myriad-dreamin.com/typst/templates/blob/main/charged-ieee/template/main.typ
```

## URL parameters

| Param | Values | Effect |
| ----- | ------ | ------ |
| `g-mode`  | `doc` / `slide` | Document mode or slide mode. |
| `g-version` | `v0.13.0`, `v0.13.1`, `v0.14.0`, `latest` | Typst compiler version. |
| `g-cors` | `true` / `false` | Use the CORS proxy or load directly. |

## Slide view

Add `?g-mode=slide` to view a Typst file as a slideshow:

```
https://gistd.myriad-dreamin.com/touying-typ/touying/blob/main/examples/simple.typ?g-mode=slide
```

Use the arrow keys to navigate. Touying-specific animation (`#pause` /
`#meanwhile`) and speaker notes are honoured.

## Loading from arbitrary URLs

Use the `any-gistd` subdomain (alias for `gistd.myriad-dreamin.com/@any`):

```
https://any-gistd.myriad-dreamin.com/github.com/typst/templates/blob/main/charged-ieee/template/main.typ
```

`any-gistd` infers the protocol from the host:

| Host | Protocol |
| ---- | -------- |
| `github.com` | git |
| `codeberg.org` | git |
| `localhost` | HTTP |
| anything else | HTTPS |

If the host isn't recognised, gistd refuses to load other resources from
the same domain (security).

## Loading without the CORS proxy

By default gistd uses `https://underleaf.mgt.workers.dev` to bypass
GitHub's missing CORS headers. To go direct, append `g-cors=false`.

## HTTP-only loading

`@http` forces HTTP regardless of the URL — useful for local dev:

```
https://gistd.myriad-dreamin.com/@http/localhost:11449/main.typ
```

## Development

```sh
pnpm install
pnpm dev    # local development
pnpm build  # production build
```

## Pitfalls

- The compiler runs in WebAssembly — first load is slow (~5 MB) but
  subsequent slides are instant.
- Gistd defaults to compiler version `latest`. Pin with `g-version=v0.14.0`
  for stable share links.
- `g-mode=slide` only works on Typst files that produce one page per
  slide — pure text documents look weird.
