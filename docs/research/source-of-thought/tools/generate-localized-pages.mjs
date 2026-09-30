// The bilingual project pages are maintained as reviewed source, not translated by
// legacy search-and-replace. This entry point remains compatible but read-only:
// it must not restore the retired microsite or overwrite the global sitemap.
import {readFileSync,readdirSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const pages=readdirSync(root).filter(f=>f.endsWith('.html'));
for(const page of pages){const text=readFileSync(resolve(root,page),'utf8');if(!text.includes('../../style.css')||!text.includes('hreflang="ja"'))throw new Error('Shared bilingual shell missing: '+page);}
console.log('PASS: reviewed bilingual pages and shared shell retained; no files rewritten.');
