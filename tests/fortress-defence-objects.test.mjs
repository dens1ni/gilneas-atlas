import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
test('two major fortresses have small separate defensive armouries without damage effects or new criteria',()=>{
 const data=read('atlas.json');
 for(const [id,objectId] of [['shadowfang','object-pyrewood-armoury'],['fenris-keep','object-fenris-armoury']]){
  const location=data.locations.find(l=>l.id===id),object=location.objects.find(o=>o.id===objectId);assert.ok(object,id);
  assert.equal(location.objects.length,2);assert.equal(object.type,'warehouse');assert.equal(object.rules.bonusValue,1);
  assert.equal(object.rules.activation,'ownership');assert.equal(object.rules.appliesTo,'all-members');assert.equal(object.rules.stacking,'additive');
  assert.deepEqual(object.modifiers.map(m=>m.text),['+1 к защите (КД) всей фракции.']);assert.ok(object.description.length>80);
 }
 assert.deepEqual(data,read('publication-v6.json'));
});
