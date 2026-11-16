import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {normalizeData} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));

test('published combat modifiers use weapon attack rolls instead of damage',()=>{
 const data=read('atlas.json');
 for(const location of data.locations)for(const object of location.objects){
  for(const modifier of object.modifiers)assert.doesNotMatch(modifier.text,/урон|damage/iu,modifier.id);
 }
 for(const [locationId,objectId,modifierId] of [
  ['military-district','object-d505a97b-c97d-5790-be8d-f82077bb9ec4','modifier-aba45063-7517-5595-8f7f-1e3444819229'],
  ['location-ecbf79ff-610a-4bde-8d16-a437954ed7a4','object-fd66d57f-f5e1-5fb2-a6f9-de2169c98459','modifier-0d6fc9c0-ae77-529d-8812-22f71b7be64d'],
 ]){
  const location=data.locations.find(record=>record.id===locationId);
  const object=location.objects.find(record=>record.id===objectId);
  const modifier=object.modifiers.find(record=>record.id===modifierId);
  assert.equal(modifier.text,'+1 к броскам атаки дальнобойным оружием всей фракции.');
  assert.equal(object.rules.activation,'ownership');
  assert.equal(object.rules.appliesTo,'all-members');
 }
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(data,read('publication-v6.json'));
});
