// Resolve packaged paths against this module, including GitHub Pages /repository/ URLs.
// Archive manifests keep their original root-prefixed paths for provenance.
const siteBase = new URL('.', import.meta.url);
const version = new URL(import.meta.url).searchParams.get('v');
export const siteUrl = path => {
  const url = new URL(String(path).replace(/^\/+/, ''), siteBase);
  if (version && url.origin === siteBase.origin && url.pathname.startsWith(siteBase.pathname + 'data/') && url.pathname.endsWith('.json')) url.searchParams.set('v', version);
  return url.href;
};
