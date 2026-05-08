/**
 * Ambient declarations for markdown-it plugins that ship JS-only.
 *
 * `@types/markdown-it-task-lists` exists upstream but is two majors
 * behind the current plugin API and triggers type-incompatibility
 * warnings. Declaring the modules locally as `any` is the standard
 * markdown-it ecosystem workaround.
 *
 * `@vscode/markdown-it-katex` doesn't ship types at all — same shim.
 */
declare module "markdown-it-task-lists";
declare module "@vscode/markdown-it-katex";

/**
 * Vite asset suffix `?url` returns the resolved URL of an arbitrary
 * file as a string. We use this to ship the pdf.js worker bundle as
 * a hashed asset that survives `vite build`.
 */
declare module "*?url" {
  const url: string;
  export default url;
}
