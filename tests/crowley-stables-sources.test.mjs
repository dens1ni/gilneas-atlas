import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {normalizeData,serializeSnapshot,deserializeSnapshot} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const STABLES='location-ea37cf4e-63d7-48d1-bb38-c5a465f16f3a';

test('current Crowley stables recover the historical Wowpedia evidence without resurrecting the removed marker',()=>{
 const data=read('atlas.json'),old=read('publication-v5.json');
 const current=data.locations.find(place=>place.id===STABLES);
 const historical=old.locations.find(place=>place.id==='crowley-stable-grounds');
 assert.equal(current.name,'Конюшни Краули');
 assert.equal(current.wowpediaUrl,historical.wowpediaUrl);
 assert.deepEqual(current.sources,[15,'family-source-3',14]);
 assert.deepEqual(current.provenance.sources,[15,'family-source-3',14]);
 assert.equal(current.provenance.confidence,'custom');
 assert.equal(current.provenance.authorScenario.ownership.basis,'explicit-user-authorship');
 assert.match(current.provenance.note,/авторск|расположен/i);
 assert.match(current.provenance.note,/не подтвержд/i);
 for(const id of current.sources){
  const source=data.sources.find(record=>record.id===id);
  assert.ok(source,id);
  assert.deepEqual(source,old.sources.find(record=>record.id===id));
  assert.ok(source.url.startsWith('https://wowpedia.fandom.com/wiki/'));
  assert.ok(source.quote);
 }
 assert.equal(data.sources.length,old.sources.length+11);
 assert.ok(!data.locations.some(place=>place.id==='crowley-stable-grounds'));
 assert.equal(data.locations.filter(place=>place.name==='Конюшни Краули').length,1);
 assert.deepEqual([current.x,current.y],[951,3392]);
 assert.equal(current.faction,'crowley');
 assert.equal(current.owner,'Дариус Краули');
 assert.equal(current.objects[0].id,'object-dc96c2df-21a4-5a20-b2b2-2b0b67489a9c');
 assert.equal(current.objects[0].modifiers[0].id,'modifier-0b87047e-ea07-5693-9758-5ca8f71f6496');
 assert.equal(current.objects[0].modifiers[0].text,'+2 к проверкам Мудрости (Уход за животными) всей фракции.');
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)),data);
 assert.deepEqual(data,read('publication-v6.json'));
});
