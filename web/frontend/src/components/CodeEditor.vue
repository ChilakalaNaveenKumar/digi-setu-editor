<!--
  CodeEditor — CodeMirror 6 wrapper for editable file viewing.

  Used by EditorPane in Mode A (current file / user opened from tree).
  Modes B (live streaming) and C (diff review) keep using Shiki read-only
  HTML — those are by definition not user-editable.

  Contract:
    Props
      path           — workspace-relative posix; drives language pack.
      initialContent — initial document text.
      readonly?      — when true, disables editing entirely.
    Emits
      update:dirty (boolean)  — bubbles up whenever the doc diverges from
                                or returns to the last saved snapshot.
      save (content)          — fired on Cmd/Ctrl-S. Parent persists.

  Why CodeMirror (not Monaco):
    Monaco bundles ~3MB and is heavyweight. CodeMirror 6 is ~200KB with
    real multi-cursor, search, brackets, autocomplete, folding — every
    table-stakes editor feature — and integrates cleanly with our
    Notion-teal dark theme via the oneDark base.
-->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { EditorState, type Extension } from "@codemirror/state";
import {
  EditorView,
  drawSelection,
  highlightActiveLine,
  highlightActiveLineGutter,
  highlightSpecialChars,
  keymap,
  lineNumbers,
} from "@codemirror/view";
import {
  defaultKeymap,
  history,
  historyKeymap,
  indentWithTab,
} from "@codemirror/commands";
import { searchKeymap, highlightSelectionMatches, search } from "@codemirror/search";
import {
  autocompletion,
  closeBrackets,
  closeBracketsKeymap,
  completionKeymap,
} from "@codemirror/autocomplete";
import {
  bracketMatching,
  defaultHighlightStyle,
  foldGutter,
  foldKeymap,
  indentOnInput,
  syntaxHighlighting,
} from "@codemirror/language";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { html } from "@codemirror/lang-html";
import { css } from "@codemirror/lang-css";
import { json } from "@codemirror/lang-json";
import { markdown } from "@codemirror/lang-markdown";
import { rust } from "@codemirror/lang-rust";
import { go } from "@codemirror/lang-go";
import { java } from "@codemirror/lang-java";
import { cpp } from "@codemirror/lang-cpp";
import { php } from "@codemirror/lang-php";
import { sql } from "@codemirror/lang-sql";
import { xml } from "@codemirror/lang-xml";
import { yaml } from "@codemirror/lang-yaml";
import { StreamLanguage } from "@codemirror/language";
import { shell } from "@codemirror/legacy-modes/mode/shell";
import { ruby } from "@codemirror/legacy-modes/mode/ruby";
import { lua } from "@codemirror/legacy-modes/mode/lua";
import { perl } from "@codemirror/legacy-modes/mode/perl";
import { dockerFile } from "@codemirror/legacy-modes/mode/dockerfile";
import { toml } from "@codemirror/legacy-modes/mode/toml";
import { properties } from "@codemirror/legacy-modes/mode/properties";
import { diff } from "@codemirror/legacy-modes/mode/diff";
import { swift } from "@codemirror/legacy-modes/mode/swift";
import {
  kotlin,
  scala,
  dart,
  csharp,
  objectiveC,
  shader,
} from "@codemirror/legacy-modes/mode/clike";
import { r } from "@codemirror/legacy-modes/mode/r";
import { powerShell } from "@codemirror/legacy-modes/mode/powershell";
import { crystal } from "@codemirror/legacy-modes/mode/crystal";
import { haskell } from "@codemirror/legacy-modes/mode/haskell";
import { fortran } from "@codemirror/legacy-modes/mode/fortran";
import { tcl } from "@codemirror/legacy-modes/mode/tcl";
import { vb } from "@codemirror/legacy-modes/mode/vb";
import { verilog } from "@codemirror/legacy-modes/mode/verilog";
import { d } from "@codemirror/legacy-modes/mode/d";
import { stex } from "@codemirror/legacy-modes/mode/stex";
import { julia } from "@codemirror/legacy-modes/mode/julia";
import { commonLisp } from "@codemirror/legacy-modes/mode/commonlisp";
import { clojure } from "@codemirror/legacy-modes/mode/clojure";
import { erlang } from "@codemirror/legacy-modes/mode/erlang";
import { groovy } from "@codemirror/legacy-modes/mode/groovy";
import { mathematica } from "@codemirror/legacy-modes/mode/mathematica";
import { nginx } from "@codemirror/legacy-modes/mode/nginx";
import { cmake } from "@codemirror/legacy-modes/mode/cmake";
import { coffeeScript } from "@codemirror/legacy-modes/mode/coffeescript";
import { elixir } from "codemirror-lang-elixir";
import { oneDark } from "@codemirror/theme-one-dark";
import { typstMode } from "../lib/typst-mode";

const props = defineProps<{
  path: string;
  initialContent: string;
  readonly?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:dirty", dirty: boolean): void;
  (e: "save", content: string): void;
}>();

const container = ref<HTMLDivElement | null>(null);

let view: EditorView | null = null;
let lastSaved = props.initialContent;
const isDirty = ref(false);

function setDirty(next: boolean): void {
  if (isDirty.value === next) return;
  isDirty.value = next;
  emit("update:dirty", next);
}

/** Map an extension or full filename to a CodeMirror language extension.
 *  Falls back to plain text (no syntax highlighting) for unknown types.
 *
 *  We deliberately use `StreamLanguage.define()` for "legacy" modes — those
 *  are battle-tested CodeMirror 5 modes ported to v6; their tokenisation is
 *  good enough for syntax colouring (we don't depend on their Lezer trees
 *  for autocomplete or folding). For first-class langs (JS/TS/Python/etc.)
 *  we use the dedicated `@codemirror/lang-*` packages which DO build a real
 *  Lezer tree and unlock all the IDE features.
 */
function languageExt(path: string): Extension | null {
  const file = path.split("/").pop()?.toLowerCase() ?? "";

  // ── Filename-only matches (no extension or canonical special name) ──
  // Order matters: a more-specific filename rule must win over a generic
  // extension rule (e.g. "Gemfile" → ruby BEFORE we look at the ".gemfile"
  // ext, which doesn't exist).
  if (file === "dockerfile" || file.endsWith(".dockerfile") || file.startsWith("dockerfile.")) {
    return StreamLanguage.define(dockerFile);
  }
  if (
    file === "makefile" ||
    file === "gnumakefile" ||
    file.endsWith(".mk") ||
    file.endsWith(".mak")
  ) {
    // No dedicated CM6 grammar for Makefile; properties is a closer
    // approximation than plain text (highlights `KEY = value` and comments).
    return StreamLanguage.define(properties);
  }
  if (file === "cmakelists.txt" || file.endsWith(".cmake")) {
    return StreamLanguage.define(cmake);
  }
  if (file === "gemfile" || file === "rakefile" || file === "podfile") {
    return StreamLanguage.define(ruby);
  }
  if (file === "vagrantfile" || file === "berksfile") {
    return StreamLanguage.define(ruby);
  }
  if (file.startsWith("nginx") && (file.endsWith(".conf") || file === "nginx.conf")) {
    return StreamLanguage.define(nginx);
  }
  if (file === ".gitignore" || file === ".gitattributes" || file === ".dockerignore") {
    return StreamLanguage.define(properties);
  }
  if (file === ".eslintrc" || file === ".babelrc" || file === ".prettierrc") {
    return json();
  }

  const ext = file.includes(".") ? file.split(".").pop() : "";
  switch (ext) {
    // ── JavaScript / TypeScript ───────────────────────────────────────
    case "ts":
    case "mts":
    case "cts":
      return javascript({ typescript: true });
    case "tsx":
      return javascript({ typescript: true, jsx: true });
    case "js":
    case "mjs":
    case "cjs":
      return javascript();
    case "jsx":
      return javascript({ jsx: true });
    // ── Python ────────────────────────────────────────────────────────
    case "py":
    case "pyi":
    case "pyw":
      return python();
    // ── Markup ────────────────────────────────────────────────────────
    case "html":
    case "htm":
    case "vue":
    case "svelte":
    case "astro":
      return html();
    case "css":
    case "scss":
    case "sass":
    case "less":
    case "styl":
      return css();
    case "json":
    case "jsonc":
    case "json5":
    case "webmanifest":
      return json();
    case "md":
    case "mdx":
    case "markdown":
      return markdown();
    case "xml":
    case "svg":
    case "plist":
    case "rss":
    case "xaml":
      return xml();
    case "yaml":
    case "yml":
      return yaml();
    // ── Systems / compiled ────────────────────────────────────────────
    case "rs":
      return rust();
    case "go":
      return go();
    case "java":
      return java();
    case "kt":
    case "kts":
      return StreamLanguage.define(kotlin);
    case "swift":
      return StreamLanguage.define(swift);
    case "scala":
    case "sbt":
      return StreamLanguage.define(scala);
    case "dart":
      return StreamLanguage.define(dart);
    case "groovy":
    case "gradle":
      return StreamLanguage.define(groovy);
    case "cs":
    case "csx":
      return StreamLanguage.define(csharp);
    case "c":
    case "h":
    case "cpp":
    case "cc":
    case "cxx":
    case "hpp":
    case "hh":
    case "hxx":
      return cpp();
    case "m":
    case "mm":
      return StreamLanguage.define(objectiveC);
    case "d":
    case "di":
      return StreamLanguage.define(d);
    case "v":
    case "sv":
    case "svh":
      return StreamLanguage.define(verilog);
    case "f":
    case "f90":
    case "f95":
    case "f03":
      return StreamLanguage.define(fortran);
    case "glsl":
    case "vert":
    case "frag":
    case "shader":
      return StreamLanguage.define(shader);
    case "php":
    case "phtml":
      return php();
    // ── Shell / config ────────────────────────────────────────────────
    case "sh":
    case "bash":
    case "zsh":
    case "ksh":
    case "fish":
    case "ash":
    case "command":
      return StreamLanguage.define(shell);
    case "toml":
      return StreamLanguage.define(toml);
    case "ini":
    case "cfg":
    case "conf":
    case "properties":
    case "env":
      return StreamLanguage.define(properties);
    case "diff":
    case "patch":
      return StreamLanguage.define(diff);
    // ── Scripting / misc ──────────────────────────────────────────────
    case "rb":
    case "rake":
    case "gemspec":
      return StreamLanguage.define(ruby);
    case "lua":
      return StreamLanguage.define(lua);
    case "pl":
    case "pm":
      return StreamLanguage.define(perl);
    case "sql":
      return sql();
    case "ps1":
    case "psm1":
    case "psd1":
      return StreamLanguage.define(powerShell);
    case "tcl":
      return StreamLanguage.define(tcl);
    case "vb":
    case "bas":
    case "vbs":
      return StreamLanguage.define(vb);
    case "coffee":
      return StreamLanguage.define(coffeeScript);
    // ── Functional ────────────────────────────────────────────────────
    case "ex":
    case "exs":
      return elixir();
    case "erl":
    case "hrl":
      return StreamLanguage.define(erlang);
    case "hs":
    case "lhs":
      return StreamLanguage.define(haskell);
    case "lisp":
    case "lsp":
    case "el":
      return StreamLanguage.define(commonLisp);
    case "clj":
    case "cljs":
    case "cljc":
    case "edn":
      return StreamLanguage.define(clojure);
    case "cr":
      return StreamLanguage.define(crystal);
    case "jl":
      return StreamLanguage.define(julia);
    // ── Statistical / scientific ──────────────────────────────────────
    case "r":
      return StreamLanguage.define(r);
    case "wls":
    case "nb":
      return StreamLanguage.define(mathematica);
    // ── Infrastructure / config / declarative ─────────────────────────
    case "tf":
    case "tfvars":
    case "hcl":
      // No first-class HCL; properties tokenises `key = value` / quoted strings
      // sensibly enough that the file is readable. Better than plain text.
      return StreamLanguage.define(properties);
    case "tex":
    case "ltx":
      return StreamLanguage.define(stex);
    // ── Typst (custom StreamLanguage in lib/typst-mode.ts) ────────────
    case "typ":
    case "typst":
      return StreamLanguage.define(typstMode);
    default:
      return null;
  }
}

function buildExtensions(): Extension[] {
  const langExt = languageExt(props.path);
  return [
    lineNumbers(),
    highlightActiveLineGutter(),
    highlightSpecialChars(),
    history(),
    foldGutter(),
    drawSelection(),
    indentOnInput(),
    syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
    bracketMatching(),
    closeBrackets(),
    autocompletion(),
    highlightActiveLine(),
    highlightSelectionMatches(),
    search({ top: true }),
    keymap.of([
      ...closeBracketsKeymap,
      ...defaultKeymap,
      ...searchKeymap,
      ...historyKeymap,
      ...foldKeymap,
      ...completionKeymap,
      indentWithTab,
      // Cmd/Ctrl-S → emit save (parent handles the actual fetch)
      {
        key: "Mod-s",
        preventDefault: true,
        run: () => {
          if (!view) return false;
          const content = view.state.doc.toString();
          lastSaved = content;
          setDirty(false);
          emit("save", content);
          return true;
        },
      },
    ]),
    oneDark,
    EditorState.readOnly.of(Boolean(props.readonly)),
    EditorView.updateListener.of((update) => {
      if (update.docChanged && view) {
        const cur = view.state.doc.toString();
        setDirty(cur !== lastSaved);
      }
    }),
    EditorView.theme({
      "&": {
        height: "100%",
        fontSize: "12.5px",
        backgroundColor: "var(--editor-bg, #1f1f23)",
      },
      ".cm-scroller": {
        fontFamily:
          "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
        lineHeight: "1.6",
      },
      ".cm-content": { padding: "8px 0" },
      ".cm-gutters": {
        backgroundColor: "var(--editor-bg, #1f1f23)",
        borderRight: "1px solid var(--border, #2a2a2e)",
        color: "var(--editor-line, #6b7280)",
      },
    }),
    ...(langExt ? [langExt] : []),
  ];
}

function makeState(content: string): EditorState {
  return EditorState.create({
    doc: content,
    extensions: buildExtensions(),
  });
}

onMounted(() => {
  view = new EditorView({
    state: makeState(props.initialContent),
    parent: container.value!,
  });
  lastSaved = props.initialContent;
  setDirty(false);
});

onBeforeUnmount(() => {
  view?.destroy();
  view = null;
});

// Re-create the editor when the file path changes (different file = fresh
// state, history reset, language pack swap).
watch(
  () => props.path,
  () => {
    if (!view) return;
    view.setState(makeState(props.initialContent));
    lastSaved = props.initialContent;
    setDirty(false);
  },
);

// External content updates (e.g. agent rewrote the file while the user
// hadn't touched it). Only swap if the user has NO local edits — otherwise
// we'd silently nuke their typing. The parent decides via `respectDirty`
// (see EditorPane). For now: respect dirty by default.
watch(
  () => props.initialContent,
  (next) => {
    if (!view || isDirty.value) return;
    if (view.state.doc.toString() === next) return;
    view.setState(makeState(next));
    lastSaved = next;
    setDirty(false);
  },
);

defineExpose({
  /** Programmatic save (e.g. parent's "Save" button). */
  save(): void {
    if (!view) return;
    const content = view.state.doc.toString();
    lastSaved = content;
    setDirty(false);
    emit("save", content);
  },
  /** Discard local edits & re-load from `initialContent`. */
  discardLocalEdits(): void {
    if (!view) return;
    view.setState(makeState(props.initialContent));
    lastSaved = props.initialContent;
    setDirty(false);
  },
  isDirty: () => isDirty.value,
});
</script>

<template>
  <div ref="container" class="h-full min-h-0 w-full overflow-hidden"></div>
</template>

<style scoped>
:deep(.cm-editor) {
  height: 100%;
}
:deep(.cm-editor.cm-focused) {
  outline: none;
}
</style>
