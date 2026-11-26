// Run the portfolio's own validators on a data folder.
//   node validate.mjs <dir with works.json + soundscape.json> <categories.json>
import { readFile } from 'node:fs/promises';
import { validateWorks } from './src/data/schema.mjs';
import { validateSoundscape } from './src/data/soundscape.mjs';
import { encodeObjectKey } from './src/lib/media.mjs';

const [dir, categoriesFile] = process.argv.slice(2);
const read = async (f) => JSON.parse(await readFile(f, 'utf8'));
const { works } = await read(`${dir}/works.json`);
const { categories } = await read(categoriesFile);
const soundscape = await read(`${dir}/soundscape.json`);
const result = {
  works: validateWorks(works, categories),
  soundscape: validateSoundscape(soundscape),
  encodedKeys: Object.fromEntries([...works.map((w) => w.videoKey), ...soundscape.tracks.map((t) => t.key)]
    .filter(Boolean).map((k) => [k, encodeObjectKey(k)])),
};
console.log(JSON.stringify(result));
