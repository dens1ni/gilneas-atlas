import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url);

test('map caption uses the rain kingdom chapter without old rose wording',async()=>{
  const html=await readFile(new URL('index.html',root),'utf8');
  assert.ok(html.includes('ИСТОРИЯ КОРОЛЕВСТВА ДОЖДЕЙ'));
  assert.ok(html.includes('Глава I. Стена Седогрива'));
  assert.ok(!html.includes('ЗЕМЛИ СЕВЕРНЫХ КОРОЛЕВСТВ'));
  assert.ok(!html.includes('Под сенью алой розы'));
});

test('map compass is absent rather than hidden by a breakpoint',async()=>{
  const html=await readFile(new URL('index.html',root),'utf8');
  assert.ok(!html.includes('class="compass"'),'Remove the actual compass element at every viewport');
  assert.ok(!html.includes('class="needle"'));
});

test('desktop faction panel has an explicit reopening control',async()=>{
  const html=await readFile(new URL('index.html',root),'utf8');
  assert.ok(/<button[^>]*id="layers-open"/.test(html));
  assert.ok(/id="layers-close"[^>]*class="square"/.test(html),'The close control works on desktop as well');
});

test('Royal Council is reachable from toolbar and chronicle',async()=>{
  const html=await readFile(new URL('index.html',root),'utf8');
  assert.ok(/<button[^>]*id="council-open"/.test(html));
  assert.ok(/<button[^>]*id="chronicle-council"/.test(html));
  assert.ok(html.includes('Королевский Совет'));
});

test('wall track is a keyboard-operable history action without changing legacy progress identifiers',async()=>{
  const html=await readFile(new URL('index.html',root),'utf8');
  assert.ok(/<button[^>]*id="wall-history-open"[^>]*type="button"/.test(html));
  assert.ok(html.includes('aria-haspopup="dialog"'));
  assert.ok(html.includes('id="wall-progress" value="10" max="100"'));
});

test('runtime export retains the exact Origins publication baseline for local-draft migration',async()=>{
  const manifest=JSON.parse(await readFile(new URL('assets/runtime-manifest.json',root),'utf8'));
  assert.ok(manifest.includes('assets/data/publication-v3.json'));
  const previous=JSON.parse(await readFile(new URL('assets/data/publication-v3.json',root),'utf8'));
  assert.equal(previous.meta.publicationRevision,'origins-dossiers-v3');
  assert.equal(previous.meta.mapRevision,'origins-map-v3');
  assert.equal(previous.locations.length,39);
  assert.ok(!Object.hasOwn(previous,'royalCouncil'));
  assert.deepEqual(previous.meta.wallConstruction,{value:10,max:100});
});

test('council, wall journal and shared types are included in site exports and CSS cascade',async()=>{
  const manifest=JSON.parse(await readFile(new URL('assets/runtime-manifest.json',root),'utf8'));
  for(const path of ['assets/js/object-types.mjs','assets/js/royal-council.mjs','assets/js/council-window.mjs','assets/js/wall-progress.mjs','assets/js/wall-journal.mjs','assets/css/royal-council.css','assets/css/wall-journal.css'])assert.ok(manifest.includes(path),path);
  const html=await readFile(new URL('index.html',root),'utf8');
  for(const path of ['assets/css/royal-council.css','assets/css/wall-journal.css'])assert.ok(html.includes('href="'+path+'"'),path);
});

test('court interaction styles follow the royal skin without overriding the later wall layout',async()=>{
  const html=await readFile(new URL('index.html',root),'utf8');
  assert.ok(html.includes('href="assets/css/court-ui.css"'));
  assert.ok(html.indexOf('assets/css/court-ui.css')>html.indexOf('assets/css/royal-windows.css'));
  assert.ok(html.indexOf('assets/css/wall-journal.css')>html.indexOf('assets/css/court-ui.css'));
  const manifest=JSON.parse(await readFile(new URL('assets/runtime-manifest.json',root),'utf8'));
  assert.ok(manifest.includes('assets/css/court-ui.css'));
});
