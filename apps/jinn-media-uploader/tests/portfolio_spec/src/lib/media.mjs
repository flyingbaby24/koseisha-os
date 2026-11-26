// Object key -> public URL. Keys are stored raw ("Meaning Hollow.mp4") exactly
// as they exist in the bucket; encoding happens here, once.

/** Percent-encode every path segment of an object key, keeping "/" separators. */
export function encodeObjectKey(key) {
  return key.split('/').map((segment) =>
    encodeURIComponent(segment).replace(/[!'()*]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`)
  ).join('/');
}

export function videoUrl(config, work) {
  return work.videoKey ? `${config.mediaBaseUrl}/${encodeObjectKey(work.videoKey)}` : null;
}

/** Root-relative when thumbnails are served by the site itself, absolute otherwise. */
export function imageUrl(config, key, { absolute = false } = {}) {
  if (!key) return null;
  const base = config.thumbnailBaseUrl || (absolute ? config.siteUrl : '');
  return `${base}/${encodeObjectKey(key)}`;
}

export function mimeFor(key) {
  const ext = key.toLowerCase().split('.').pop();
  return { mp4: 'video/mp4', m4v: 'video/mp4', webm: 'video/webm', mov: 'video/quicktime',
           webp: 'image/webp', jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', avif: 'image/avif' }[ext] ?? 'application/octet-stream';
}

/** 84.93 -> "1:25" */
export function formatDuration(seconds) {
  if (seconds == null) return null;
  const s = Math.round(seconds);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return h ? `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}` : `${m}:${String(sec).padStart(2, '0')}`;
}

/** 84.93 -> "PT1M25S" (schema.org / ISO 8601) */
export function isoDuration(seconds) {
  if (seconds == null) return null;
  const s = Math.round(seconds);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return `PT${h ? `${h}H` : ''}${m ? `${m}M` : ''}${sec || (!h && !m) ? `${sec}S` : ''}`;
}
