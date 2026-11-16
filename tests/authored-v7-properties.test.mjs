import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {normalizeData} from '../assets/js/model.mjs';
const data=JSON.parse(fs.readFileSync(new URL('../assets/data/atlas.json',import.meta.url)));
const previous=JSON.parse(fs.readFileSync(new URL('../assets/data/publication-v6.json',import.meta.url)));
const find=id=>data.locations.find(l=>l.id===id);
test('v7 preserves existing literal records and adds exactly 21 requested properties',()=>{
 assert.equal(data.meta.publicationRevision,'authored-estates-v7');assert.equal(data.locations.length,previous.locations.length+21);
 for(const l of previous.locations)assert.ok(find(l.id));
 for(const [group,n] of Object.entries({'blackwald':4,'tempests-reach':2,'keel-harbor':6,'mossy-roofs':1,'emberstone-village':3,'hayward-fishery':3,'road-gates':2})){
  const entries=data.locations.filter(l=>l.id.startsWith(`location-v7-${group}-`));assert.equal(entries.length,n);
  for(const l of entries){assert.equal(l.objects.length,1);assert.equal(l.objects[0].rules.activation,'ownership');assert.equal(l.objects[0].rules.bonusValue,1);assert.equal(l.objects[0].modifiers.length,1);assert.match(l.objects[0].modifiers[0].text,/^\+1/);assert.ok(l.description.length>80);}
 }
 assert.doesNotThrow(()=>normalizeData(data));
});
test('requested ownership and personal municipal stewardship are distinct',()=>{
 assert.equal(find('northern-headlands').faction,'candren');assert.equal(find('pyrewood').owner,'Лорд-мэр Моррисон');assert.equal(find('pyrewood').faction,'silverlaine');
 for(const id of ['location-b415ddf5-f12a-4421-829f-e8723bdaa1d4','location-a4bf5eb0-1154-4519-9400-f17ced83a1d9','location-8288bc4e-bb08-45d9-ace3-bc878fe7e8ba'])assert.equal(find(id).faction,'ashbury');
 assert.equal(find('location-54cebe0e-8a63-43c7-86d2-b85f6edf2732').faction,'gilneas');
 assert.equal(find('location-raft-estate').x,1132.67);assert.equal(find('location-raft-estate').y,2838);
});
test('new homes are linked, royal guards are not, ruins explicitly destroyed',()=>{
 const parents={'blackwald':'blackwald','tempests-reach':'tempests-reach','keel-harbor':'keel-harbor','mossy-roofs':'location-fb88bb30-c639-4f75-a142-92445555a772','emberstone-village':'emberstone-village','hayward-fishery':'hayward-fishery'};
 for(const [group,id] of Object.entries(parents)){const p=find(id);assert.equal(p.isLocation,true);for(const l of data.locations.filter(l=>l.id.startsWith(`location-v7-${group}-`)))assert.ok(p.linkedLocationIds.includes(l.id));}
 for(const l of data.locations.filter(l=>l.id.startsWith('location-v7-blackwald-'))){assert.equal(l.destroyed,true);assert.equal(l.faction,'gilneas');}
 for(const l of data.locations.filter(l=>l.id.startsWith('location-v7-road-gates-'))){assert.equal(l.faction,'gilneas');assert.ok(!data.locations.some(p=>p.linkedLocationIds?.includes(l.id)));}
});
test('all eleven houses have Council records; political domains and party pools retained',()=>{
 const houses=data.factions.filter(f=>f.name.includes('Дом'));assert.equal(houses.length,11);
 for(const f of houses){const m=data.royalCouncil.members.filter(m=>m.kind==='faction'&&m.refId===f.id);assert.equal(m.length,1);assert.ok(m[0].propertyInfluenceAssessment.kingdom<=100);}
 assert.deepEqual(data.royalCouncil.influence,previous.royalCouncil.influence);
 assert.equal(JSON.stringify(data.territoryGrid.realmLayout.domainCells),JSON.stringify(previous.territoryGrid.realmLayout.domainCells));
 assert.deepEqual(data.meta.wallConstruction,previous.meta.wallConstruction);
});
