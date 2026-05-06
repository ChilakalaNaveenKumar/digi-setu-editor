import { createPinia } from "pinia";
import { createApp } from "vue";
import { addCollection } from "@iconify/vue";
import materialIconTheme from "@iconify-json/material-icon-theme/icons.json";
import codicon from "@iconify-json/codicon/icons.json";
import App from "./App.vue";
import "./app.css";

// Pre-register Iconify collections so file/folder/action icons resolve
// instantly without an API round-trip. Material Icon Theme is the
// standard "VS Code Material Icon Theme" pack (per-language colours);
// codicon is Microsoft's official VS Code action-icon set (new file,
// refresh, collapse-all, etc.).
addCollection(materialIconTheme as never);
addCollection(codicon as never);

// Apply dark mode + chosen palette globally. To swap palette: change the
// class name below to "theme-linear" / "theme-cursor" / "theme-vercel" /
// "theme-stripe" — each is defined in app.css.
document.documentElement.classList.add("dark", "theme-notion");

createApp(App).use(createPinia()).mount("#app");
