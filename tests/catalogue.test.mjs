import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

// One trace of the real catalogue, not a fabricated fixture counted as lore.
test('published atlas uses the chosen epoch and exposes three sovereign realms with separately colored houses', async()=>{
  const {normalizeData,sovereignOf}=await import('../assets/js/model.mjs');
  const json=await readFile(new URL('../assets/data/atlas.json',import.meta.url),'utf8');
  const data=normalizeData(JSON.parse(json));
  assert.equal(data.meta.width,3526);assert.equal(data.meta.height,4548);
  for(const name of ['Королевство Гилнеас','Королевство Даларан','Королевство Лордерон'])assert.ok(data.factions.some(f=>f.name===name&&f.parent===null),name);
  for(const name of ['Дом Седогривов','Дом Краули'])assert.ok(data.factions.some(f=>f.name===name),name);
  const g=data.factions.find(f=>f.name==='Королевство Гилнеас');
  const c=data.factions.find(f=>f.name==='Дом Краули');
  assert.equal(sovereignOf(data.factions,c.id),g.id);
  assert.notEqual(c.color,g.color);
  assert.ok(!data.locations.some(l=>/Стена Седогрива|Кратер Даларана|Подгород|Лагерь Отрекшихся/.test(l.name)));
  for(const l of data.locations)assert.ok(l.provenance?.sources?.length||l.provenance?.confidence==='custom',l.name+' needs evidence');
  assert.ok(data.locations.find(l=>l.id==='gilneas-city').owner.includes('Генн'));
  assert.ok(data.locations.find(l=>l.id==='ambermill').owner.includes('Краули'));
  assert.ok(data.locations.find(l=>l.id==='pyrewood').owner.includes('Краули'));
});
