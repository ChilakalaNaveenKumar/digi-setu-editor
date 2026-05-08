/**
 * Build a nested tree from a flat list of FileEntry. Pure / no Vue. Tested
 * by feeding into FileTreePane.vue. Folders are inferred from path segments
 * even if the watcher doesn't emit explicit dir entries (more resilient).
 */

import type { FileEntry } from "../types/rpc";

export interface TreeNode {
  /** Folder/file name (last segment). */
  name: string;
  /** Full workspace-relative posix path. */
  path: string;
  isDir: boolean;
  /** Children, sorted: folders first, then files, both alpha. */
  children: TreeNode[];
  /** File size in bytes (0 for folders). */
  size: number;
  mtime: number;
}

function makeFolder(name: string, path: string): TreeNode {
  return { name, path, isDir: true, children: [], size: 0, mtime: 0 };
}

export function buildTree(entries: FileEntry[]): TreeNode[] {
  const root = makeFolder("", "");
  const folderIndex = new Map<string, TreeNode>([["", root]]);

  for (const entry of entries) {
    const segments = entry.path.split("/").filter(Boolean);
    if (segments.length === 0) continue;

    // Walk/create folder chain.
    let parent = root;
    for (let i = 0; i < segments.length - 1; i++) {
      const folderPath = segments.slice(0, i + 1).join("/");
      let folder = folderIndex.get(folderPath);
      if (!folder) {
        folder = makeFolder(segments[i], folderPath);
        folderIndex.set(folderPath, folder);
        parent.children.push(folder);
      }
      parent = folder;
    }

    const name = segments[segments.length - 1];
    if (entry.is_dir) {
      let folder = folderIndex.get(entry.path);
      if (!folder) {
        folder = makeFolder(name, entry.path);
        folderIndex.set(entry.path, folder);
        parent.children.push(folder);
      } else {
        folder.mtime = Math.max(folder.mtime, entry.mtime);
      }
    } else {
      parent.children.push({
        name,
        path: entry.path,
        isDir: false,
        children: [],
        size: entry.size,
        mtime: entry.mtime,
      });
    }
  }

  // Sort each folder's children: dirs first, alpha within group.
  function sortRecursive(node: TreeNode): void {
    node.children.sort((a, b) => {
      if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    node.children.forEach(sortRecursive);
  }
  sortRecursive(root);

  return root.children;
}

/** Pick a one-letter file-type marker from extension. Cheap and language-agnostic. */
export function fileGlyph(name: string): string {
  const ext = name.includes(".") ? name.split(".").pop()!.toLowerCase() : "";
  const map: Record<string, string> = {
    typ: "T",
    pdf: "P",
    png: "I",
    jpg: "I",
    jpeg: "I",
    svg: "I",
    gif: "I",
    webp: "I",
    md: "M",
    json: "J",
    yaml: "Y",
    yml: "Y",
    toml: "T",
    py: "P",
    js: "J",
    ts: "T",
    vue: "V",
    css: "C",
    html: "H",
    sh: "$",
    txt: "—",
  };
  return map[ext] ?? "·";
}

/** Format file size for display in the tree. */
export function shortSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}k`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}M`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)}G`;
}
