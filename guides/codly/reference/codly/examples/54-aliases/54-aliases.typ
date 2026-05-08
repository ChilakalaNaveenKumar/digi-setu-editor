#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#import "@preview/codly-languages:0.1.7": *
#show: codly-init

#codly(
  languages: codly-languages,
  aliases: ("cuda": "c++"),
)
```cuda
int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
```
