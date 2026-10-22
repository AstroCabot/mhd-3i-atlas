import { siteUrl } from './site-paths.js';

// Retain compressed batches across routes. Decoded images belong to their player.
// At most 32 MiB is retained, rather than thousands of decoded 768px textures.
const completed = new Map();
const MAX_BYTES = 32 * 1024 * 1024;
let retainedBytes = 0;
function remember(url, blob) {
  if (completed.has(url)) return;
  completed.set(url, blob); retainedBytes += blob.size;
  while (retainedBytes > MAX_BYTES && completed.size > 1) {
    const [key, oldest] = completed.entries().next().value;
    retainedBytes -= oldest.size; completed.delete(key);
  }
}

export function createFrameCache(manifest, onReady) {
  const index = new Map(), pending = new Map(), failed = new Set();
  let active = 0, disposed = false;
  for (const model of Object.values(manifest.models)) {
    const sequence = model.frameSequence;
    for (const [field, rows] of Object.entries(sequence.fields)) {
      for (const row of rows) {
        const pack = sequence.packs?.[field]?.[row.pack];
        if (pack) index.set(row.url, {row, pack});
      }
    }
  }
  function pump() {
    if (disposed) return;
    for (const entry of pending.values()) {
      if (active >= 4) break;
      if (entry.started) continue;
      entry.started = true; active++;
      const timer=setTimeout(()=>entry.controller.abort(new DOMException('Field batch timed out','TimeoutError')),3000);
      (async () => {
        try {
          const response = await fetch(siteUrl(entry.pack.url), {signal: entry.controller.signal, cache: 'force-cache', priority: 'low'});
          if (!response.ok) throw new Error(`Field batch ${response.status}`);
          const bytes = await response.arrayBuffer();
          if (bytes.byteLength !== entry.pack.bytes) throw new Error('Incomplete field batch');
          if (globalThis.crypto?.subtle) {
            const digest = await crypto.subtle.digest('SHA-256', bytes);
            const hex = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
            if (hex !== entry.pack.sha256) throw new Error('Changed field batch');
          }
          if (!disposed && !entry.controller.signal.aborted) {
            remember(entry.pack.url, new Blob([bytes])); onReady();
          }
        } catch (error) {
          // The original individual images remain available if a batch fails.
          if (!entry.controller.signal.aborted||entry.controller.signal.reason?.name==='TimeoutError') failed.add(entry.pack.url);
        } finally {
          clearTimeout(timer);
          if (pending.get(entry.pack.url) === entry) pending.delete(entry.pack.url);
          entry.resolve();
          active--; pump();
        }
      })();
    }
  }
  return {
    get packed() { return index.size > 0; },
    get stats() { return {retainedBytes, packs:completed.size, pending:pending.size}; },
    source(url) {
      const item = index.get(url), blob = item && completed.get(item.pack.url);
      if (!blob) return null;
      completed.delete(item.pack.url); completed.set(item.pack.url, blob);
      return blob.slice(item.row.offset, item.row.offset + item.row.bytes, 'image/webp');
    },
    has(url) { const item = index.get(url); return Boolean(item && completed.has(item.pack.url)); },
    failed(url) { return failed.has(index.get(url)?.pack.url); },
    prefetch(urls) {
      if (disposed) return Promise.resolve();
      const wanted = new Map();
      for (const url of urls) {
        const pack = index.get(url)?.pack;
        if (pack) wanted.set(pack.url, pack);
      }
      for (const [url, entry] of pending) {
        if (!wanted.has(url)) { pending.delete(url); entry.controller.abort(); entry.resolve(); }
      }
      for (const [url, pack] of wanted) {
        if (!completed.has(url) && !pending.has(url) && !failed.has(url)) {
          let resolve;
          const done=new Promise(finish=>{resolve=finish;});
          pending.set(url, {pack, controller: new AbortController(), started: false, done, resolve});
        }
      }
      pump();
      return Promise.all([...wanted.keys()].map(url=>pending.get(url)?.done));
    },
    destroy() {
      disposed = true;
      for (const entry of pending.values()) {entry.controller.abort();entry.resolve();}
      pending.clear();
    },
  };
}
