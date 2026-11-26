// Work record schema + validation. Shared by every data driver so a future D1
// driver returns exactly the same shape as the JSON one.
//
// "Not registered" is always null (scalars) or [] (lists). Never fill unknown
// lyrics, descriptions, genres etc. with invented text.

export const STATUSES = ['draft', 'published', 'unlisted', 'archived'];

// A text field is either a plain string (same in every language) or a map of
// locale -> string, e.g. { "ja": "…", "en": "…" }.
const isText = (v) => typeof v === 'string' ? v.trim() !== '' :
  (v && typeof v === 'object' && !Array.isArray(v) && Object.values(v).every((s) => typeof s === 'string'));
const isNullableText = (v) => v === null || isText(v);
const isTextList = (v) => Array.isArray(v) && v.every(isText);
const isDate = (v) => typeof v === 'string' && /^\d{4}(-\d{2}(-\d{2})?)?$/.test(v);
const isKey = (v) => typeof v === 'string' && v !== '' && !v.startsWith('/') && !/^[a-z]+:\/\//i.test(v) && !v.split('/').includes('..');

export const FIELDS = {
  id:              { required: true,  check: (v) => typeof v === 'string' && /^[a-z0-9][a-z0-9-]*$/.test(v) },
  slug:            { required: true,  check: (v) => typeof v === 'string' && /^[a-z0-9]+(-[a-z0-9]+)*$/.test(v) },
  category:        { required: true,  check: (v) => typeof v === 'string' && v !== '' },
  title:           { required: true,  check: isText },
  artist:          { required: false, check: isNullableText },
  description:     { required: false, check: isNullableText },
  lyrics:          { required: false, check: isNullableText },
  genre:           { required: false, check: isNullableText },
  themes:          { required: false, check: isTextList, default: () => [] },
  tags:            { required: false, check: isTextList, default: () => [] },
  createdDate:     { required: false, check: (v) => v === null || isDate(v) },
  publishedDate:   { required: false, check: (v) => v === null || isDate(v) },
  videoKey:        { required: false, check: (v) => v === null || isKey(v) },
  thumbnailKey:    { required: false, check: (v) => v === null || isKey(v) },
  posterKey:       { required: false, check: (v) => v === null || isKey(v) },
  duration:        { required: false, check: (v) => v === null || (typeof v === 'number' && v > 0) },
  width:           { required: false, check: (v) => v === null || (Number.isInteger(v) && v > 0) },
  height:          { required: false, check: (v) => v === null || (Number.isInteger(v) && v > 0) },
  productionTools: { required: false, check: isTextList, default: () => [] },
  relatedArticles: { required: false, default: () => [], check: (v) => Array.isArray(v) && v.every((a) =>
                       a && isText(a.title) && typeof a.url === 'string' && /^https?:\/\//.test(a.url)) },
  relatedWorks:    { required: false, check: (v) => Array.isArray(v) && v.every((s) => typeof s === 'string'), default: () => [] },
  language:        { required: false, check: (v) => v === null || (typeof v === 'string' && /^[a-z]{2,3}(-[A-Za-z0-9]+)*$/.test(v)) },
  status:          { required: true,  check: (v) => STATUSES.includes(v) },
};

/** Fill optional fields with their "not registered" value and freeze. */
export function normalizeWork(raw) {
  const work = {};
  for (const [name, def] of Object.entries(FIELDS)) {
    work[name] = raw[name] !== undefined ? raw[name] : (def.default ? def.default() : null);
  }
  return Object.freeze(work);
}

/** Returns a list of human-readable problems; empty when the collection is valid. */
export function validateWorks(works, categories) {
  const problems = [];
  const ids = new Set();
  const slugs = new Set();
  const categoryIds = new Set(categories.map((c) => c.id));
  for (const [i, raw] of works.entries()) {
    const label = raw?.id ?? `#${i}`;
    for (const key of Object.keys(raw)) if (!FIELDS[key]) problems.push(`${label}: unknown field "${key}"`);
    for (const [name, def] of Object.entries(FIELDS)) {
      const v = raw[name];
      if (v === undefined) { if (def.required) problems.push(`${label}: missing "${name}"`); continue; }
      if (!def.check(v)) problems.push(`${label}: invalid "${name}": ${JSON.stringify(v)}`);
    }
    if (ids.has(raw.id)) problems.push(`${label}: duplicate id`);
    ids.add(raw.id);
    const slugKey = `${raw.category}/${raw.slug}`;
    if (slugs.has(slugKey)) problems.push(`${label}: duplicate slug "${slugKey}"`);
    slugs.add(slugKey);
    if (raw.category && !categoryIds.has(raw.category)) problems.push(`${label}: unknown category "${raw.category}"`);
    if (raw.status === 'published' && raw.category === 'music-videos') {
      for (const need of ['videoKey', 'thumbnailKey', 'duration', 'width', 'height']) {
        if (raw[need] == null) problems.push(`${label}: published music video needs "${need}"`);
      }
    }
  }
  for (const raw of works) {
    for (const ref of raw.relatedWorks ?? []) {
      if (!ids.has(ref)) problems.push(`${raw.id}: relatedWorks references unknown id "${ref}"`);
      if (ref === raw.id) problems.push(`${raw.id}: relatedWorks references itself`);
    }
  }
  return problems;
}
