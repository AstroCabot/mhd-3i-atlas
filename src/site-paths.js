// Resolve packaged paths against this module, including GitHub Pages /repository/ URLs.
// Archive manifests keep their original root-prefixed paths for provenance.
const siteBase = new URL('.', import.meta.url);
export const siteUrl = path => new URL(String(path).replace(/^\/+/, ''), siteBase).href;
