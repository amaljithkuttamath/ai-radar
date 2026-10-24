import { mkdir, copyFile } from 'node:fs/promises';
const root = new URL('./', import.meta.url);
await mkdir(new URL('vendor/', root), { recursive: true });
for (const [source, destination] of [
  ['marked/lib/marked.esm.js', 'marked.js'],
  ['marked/LICENSE', 'marked.LICENSE.md'],
  ['dompurify/dist/purify.es.mjs', 'purify.js'],
  ['dompurify/LICENSE', 'DOMPurify.LICENSE'],
]) await copyFile(new URL(`node_modules/${source}`, root), new URL(`vendor/${destination}`, root));
