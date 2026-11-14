import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

// Runtime ZIP must keep the same publish root as the real repository.
test('runtime manifest contains every imported module and both map-activity layers', async()=>{
  const files=JSON.parse(await readFile(new URL('../assets/runtime-manifest.json',import.meta.url),'utf8'));
  assert.equal(new Set(files).size,files.length);
  for(const required of ['index.html','.nojekyll','.github/workflows/deploy-pages.yml','assets/data/atlas.json','assets/maps/gilneas-origins-enhanced.webp','assets/maps/origins-inactive-mask.png','assets/maps/origins-inactive-mist.webp','assets/js/heraldry.mjs','assets/js/map-publication.mjs','assets/css/royal-windows.css','assets/js/app.mjs','assets/js/model.mjs','assets/js/ui.mjs','assets/js/editor.mjs','assets/js/export.mjs','assets/js/chronicle.mjs','assets/js/icons.mjs'])assert.ok(files.includes(required),required);
  for(const file of files) {
    if(file==='assets/data/atlas.json')continue;
    await readFile(new URL('../'+file,import.meta.url));
  }
  const html=await readFile(new URL('../index.html',import.meta.url),'utf8');
  assert.ok(!html.includes('src="/assets/'));
  assert.ok(!html.includes('href="/assets/'));
  assert.deepEqual(await readFile(new URL('../assets/export/deploy-pages.yml',import.meta.url)),await readFile(new URL('../.github/workflows/deploy-pages.yml',import.meta.url)),'Public export copy must equal the real deployment config');
});
