import test from 'node:test';
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import fs from 'node:fs';
import {effectiveFaction,normalizeData,serializeSnapshot,deserializeSnapshot} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
test('Marley receives both Emberstone holdings and every existing ore and repair object with a same-faction compensation',()=>{
 const data=read('atlas.json'),noble=data.nobles.find(n=>n.id==='noble-marley');
 assert.equal(noble.name,'Лорд Марли');assert.equal(noble.house,'marley');
 for(const id of ['emberstone-village','emberstone-mine']){
  const location=data.locations.find(l=>l.id===id);assert.equal(location.faction,'marley',id);assert.equal(location.owner,noble.name,id);
  for(const object of location.objects){assert.equal(effectiveFaction(location,object),'marley',object.id);assert.equal(object.owner,noble.name,object.id);}
 }
 const mine=data.locations.find(l=>l.id==='emberstone-mine'),village=data.locations.find(l=>l.id==='emberstone-village');
 for(const id of ['object-2cd23821-608a-534c-9d26-125f4dd6fba5','object-emberstone-copper-deposit','object-emberstone-tin-deposit'])assert.ok(mine.objects.some(o=>o.id===id));
 for(const id of ['object-043cd8bc-00a8-57c7-9ab5-bd58cb000164','object-emberstone-ore-crushing-waterwheel'])assert.ok(village.objects.some(o=>o.id===id));
 const lamp=mine.objects.find(o=>o.id==='object-2cd23821-608a-534c-9d26-125f4dd6fba5');
 const compensation=village.objects.find(o=>o.id===lamp.rules.compensatedByObjectId);assert.ok(compensation,'Lamp drawback needs compensation in another Marley holding');
 assert.equal(compensation.rules.compensatesObjectId,lamp.id);assert.equal(compensation.rules.bonusValue,2);
 assert.equal(compensation.modifiers[0].text,'+2 '+lamp.modifiers.find(m=>m.kind==='penalty').text.slice(3));
 assert.ok(isDeepStrictEqual(data.territoryGrid,read('publication-v6.json').territoryGrid), 'Marley holdings retain the current explicitly redrawn grid');
 assert.equal(data.territoryGrid.migration.method,'author-full-realm-layout');
 assert.deepEqual(data.territories,[]);
 assert.deepEqual(normalizeData(data),data);assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)),data);assert.deepEqual(data,read('publication-v6.json'));
});
