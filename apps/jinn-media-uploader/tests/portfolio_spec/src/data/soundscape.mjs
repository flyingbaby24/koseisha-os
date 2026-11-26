// Ambient soundscape configuration (data/soundscape.json), validated at build time.
//
// track: {
//   id:    short name, used in logs                       (required)
//   key:   object key in the bucket, unencoded            (required)  e.g. "audio/archive-01.m4a"
//   gain:  linear level trim, 0.1 – 2 (default 1)
//   start: seconds to begin from when the track comes in  (default 0)
//   end:   seconds at which to hand over to the next one  (default: end of file)
// }
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { encodeObjectKey } from '../lib/media.mjs';

const FILE = fileURLToPath(new URL('../../data/soundscape.json', import.meta.url));

export function validateSoundscape(raw) {
  const problems = [];
  if (!['synth', 'none'].includes(raw.placeholder ?? 'none')) problems.push(`placeholder must be "synth" or "none"`);
  if (raw.crossfade !== undefined && !(typeof raw.crossfade === 'number' && raw.crossfade >= 0.5 && raw.crossfade <= 30)) problems.push('crossfade must be 0.5–30 seconds');
  if (!Array.isArray(raw.tracks)) problems.push('tracks must be a list');
  const ids = new Set();
  for (const [i, t] of (raw.tracks ?? []).entries()) {
    const label = t?.id ?? `#${i}`;
    if (typeof t?.id !== 'string' || !/^[a-z0-9][a-z0-9-]*$/.test(t.id)) problems.push(`${label}: invalid id`);
    if (ids.has(t?.id)) problems.push(`${label}: duplicate id`);
    ids.add(t?.id);
    if (typeof t?.key !== 'string' || !t.key || t.key.startsWith('/') || /^[a-z]+:\/\//i.test(t.key) || t.key.split('/').includes('..')) problems.push(`${label}: invalid key`);
    else if (!/\.(m4a|mp4|aac|mp3|ogg|opus|wav|flac)$/i.test(t.key)) problems.push(`${label}: key is not an audio file`);
    if (t?.gain !== undefined && !(typeof t.gain === 'number' && t.gain >= 0.1 && t.gain <= 2)) problems.push(`${label}: gain must be 0.1–2`);
    for (const f of ['start', 'end']) if (t?.[f] !== undefined && !(typeof t[f] === 'number' && t[f] >= 0)) problems.push(`${label}: ${f} must be seconds`);
    if (typeof t?.start === 'number' && typeof t?.end === 'number' && t.end <= t.start + 1) problems.push(`${label}: end must be after start`);
  }
  return problems;
}

/** What the page receives: URLs resolved against the audio base, nothing else. */
export async function loadSoundscape(config, raw) {
  raw ??= JSON.parse(await readFile(FILE, 'utf8'));
  const problems = validateSoundscape(raw);
  if (problems.length) throw new Error(`Invalid soundscape data:\n- ${problems.join('\n- ')}`);
  return {
    placeholder: raw.placeholder ?? 'none',
    crossfade: raw.crossfade ?? 8,
    tracks: raw.tracks.map((t) => ({ id: t.id, url: `${config.audioBaseUrl}/${encodeObjectKey(t.key)}`, gain: t.gain ?? 1, ...(t.start ? { start: t.start } : {}), ...(t.end ? { end: t.end } : {}) })),
  };
}
