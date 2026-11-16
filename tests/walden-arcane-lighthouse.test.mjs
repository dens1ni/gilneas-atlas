import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {effectiveFaction,normalizeData,serializeSnapshot,deserializeSnapshot} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const LIGHTHOUSE='location-e8c8f59c-83ac-49ff-819f-9708a9734ff1';

test('Walden has an authored interest in arcane knowledge while his personal practice remains a rumor',()=>{
 const data=read('atlas.json');
 const house=data.factions.find(faction=>faction.id==='walden');
 const noble=data.nobles.find(person=>person.id==='noble-walden');
 for(const record of [house,noble]){
  assert.match(record.description,/магическ[\p{L}]* знани|арканн[\p{L}]* знани/iu);
  assert.match(record.description,/слух|говорят/i);
  assert.match(record.description,/магии Порядка|магию Порядка/i);
  assert.match(record.description,/арканистик/i);
  assert.equal(record.provenance.authorScenario.arcanePatronage.basis,'explicit-user-authorship');
  assert.equal(record.provenance.authorScenario.arcanePatronage.canonicalEvidence,false);
  assert.equal(record.provenance.authorScenario.arcanePatronage.personalPractice,'rumor');
 }
 assert.equal(noble.lifeStatus,'unknown');
 assert.equal(noble.house,'walden');
});

test('the renamed southern lighthouse hosts royal mages and preserves its ID, maritime role and compensation',()=>{
 const data=read('atlas.json');
 const lighthouse=data.locations.find(place=>place.id===LIGHTHOUSE);
 assert.equal(lighthouse.name,'Маяк Звёздного Порядка');
 assert.equal(lighthouse.type,'lighthouse');
 assert.equal(lighthouse.faction,'walden');
 assert.equal(lighthouse.owner,'Лорд Вальден');
 assert.deepEqual([lighthouse.x,lighthouse.y],[2517,3552]);
 assert.ok(lighthouse.aliases.includes('Южный маяк'));
 assert.match(lighthouse.description,/магическ[\p{L}]* изыскан/iu);
 assert.match(lighthouse.description,/королевск[\p{L}]* маг/iu);
 assert.match(lighthouse.description,/разрознен|порознь/i);
 assert.match(lighthouse.description,/суд|морск|корабл/i);
 assert.equal(lighthouse.objects.length,3);
 const gallery=lighthouse.objects.find(object=>object.id==='object-8280e8da-2f21-5bd7-835d-eb53263d0c3a');
 assert.deepEqual(gallery.modifiers,[{id:'modifier-c4cb130f-f81b-52a3-9173-6e7c17acc941',kind:'bonus',text:'+2 к проверкам Мудрости (Внимательность) всей фракции.'}]);
 assert.equal(gallery.rules.compensatesObjectId,'object-5072fed6-b3c0-500c-898a-5f9e709e2689');
 const additions=[
  ['object-walden-arcane-library','library','+1 к проверкам Интеллекта (Магия) всей фракции.'],
  ['object-walden-prism-laboratory','workshop','+1 к проверкам Интеллекта (Расследование) всей фракции.'],
 ];
 for(const [id,type,effect] of additions){
  const object=lighthouse.objects.find(record=>record.id===id);assert.ok(object,id);
  assert.equal(object.type,type);
  assert.equal(effectiveFaction(lighthouse,object),'walden');
  assert.equal(object.owner,'Лорд Вальден');
  assert.equal(object.rules.activation,'ownership');
  assert.equal(object.rules.scope,'faction');
  assert.equal(object.rules.appliesTo,'all-members');
  assert.equal(object.rules.bonusValue,1);
  assert.equal(object.modifiers.length,1);
  assert.equal(object.modifiers[0].kind,'bonus');
  assert.equal(object.modifiers[0].text,effect);
  assert.doesNotMatch(object.modifiers[0].text,/при |если|после|отдых|подготов|следующ|минут/i);
 }
 const parent=data.locations.find(place=>place.id==='tempests-reach');
 assert.ok(parent.linkedLocationIds.includes(LIGHTHOUSE));
 assert.equal(data.locations.length,86);
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)),data);
 assert.deepEqual(data,read('publication-v6.json'));
});
