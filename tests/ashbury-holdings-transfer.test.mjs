import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {effectiveFaction,normalizeData} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));

test('Bradshaw Mill and Stormglen with all their objects belong to House Ashbury',()=>{
 const data=read('atlas.json'),house=data.factions.find(faction=>faction.id==='ashbury');
 assert.equal(house.name,'Дом Эшбери');
 for(const id of ['bradshaw-mill','stormglen']){
  const location=data.locations.find(place=>place.id===id);assert.ok(location,id);
  assert.equal(location.faction,'ashbury',id);
  assert.equal(location.owner,house.ruler,id);
  assert.ok(location.objects.length>0,id);
  for(const object of location.objects){
   assert.equal(effectiveFaction(location,object),'ashbury',object.id);
   assert.equal(object.owner,house.ruler,object.id);
  }
 }
 assert.deepEqual(data.locations.find(place=>place.id==='stormglen').linkedLocationIds,['bradshaw-mill','ferry-stormglen','location-8288bc4e-bb08-45d9-ace3-bc878fe7e8ba','location-52d50172-b218-4b6b-be09-eccd9fb419ce']);
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(data,read('publication-v6.json'));
});
