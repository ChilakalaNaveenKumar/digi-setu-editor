// Integration — Codly + touying-raw for animated code reveals.
#import "@preview/touying:0.7.3": *
#import themes.simple: *
#import "@preview/codly:1.3.0": *
#import "@preview/codly-languages:0.1.10": *

#show: codly-init.with()
#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-common(preamble: {
    codly(languages: codly-languages)
  }),
)

== First Slide
#raw(lang: "rust", block: true, ```
pub fn main() {
  println!("Hello, world!");
}
```.text)

== Animated Code
#touying-raw(lang: "python", ```
def greet(name):
// pause
    return f"Hello, {name}!"
// pause
print(greet("World"))
```)
