import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {effectiveFaction,normalizeData,sovereignOf} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const RAFT='raft';
const CARETAKER='location-544521a1-babb-4fea-af73-6ebb91c476e0';
const TRANSFERRED=['keel-harbor',CARETAKER,'aderics-repose','the-headlands'];
const place=(data,id)=>{const location=data.locations.find(record=>record.id===id);assert.ok(location,id);return location;};

test('House Raft owns the four requested canonical places and all their own objects',()=>{
 const data=read('atlas.json'),house=data.factions.find(faction=>faction.id===RAFT);
 assert.ok(house,'Create the explicitly requested House Raft');
 assert.equal(house.name,'Дом Рафт');
 assert.equal(house.parent,'gilneas');
 assert.equal(house.ruler,'','Do not invent a named lord or a new Council seat');
 assert.equal(sovereignOf(data.factions,RAFT),'gilneas');
 assert.equal(data.factions.filter(faction=>faction.name==='Дом Рафт').length,1);
 for(const id of TRANSFERRED){
  const location=place(data,id);
  assert.equal(location.faction,RAFT,id);
  assert.equal(location.owner,'Дом Рафт',id);
  for(const object of location.objects){
   assert.equal(effectiveFaction(location,object),RAFT,object.id);
   assert.equal(object.owner,'Дом Рафт',object.id);
  }
 }
 assert.equal(place(data,'northern-headlands').faction,'gilneas','The distinct Northern Headlands are not part of this request');
 assert.equal(place(data,'location-a4bf5eb0-1154-4519-9400-f17ced83a1d9').faction,'gilneas','Do not transfer the other cemetery caretaker');
 assert.deepEqual(normalizeData(data),data);
});

test('a new House Raft estate is a nearby dry-land canonical child of Keel Harbor',()=>{
 const data=read('atlas.json'),estate=place(data,'location-raft-estate'),harbor=place(data,'keel-harbor');
 assert.equal(estate.name,'Поместье Дома Рафт');
 assert.equal(estate.type,'estate');
 assert.equal(estate.faction,RAFT);
 assert.equal(estate.owner,'Дом Рафт');
 assert.deepEqual([estate.x,estate.y],[1163,2827]);
 assert.ok(Math.hypot(estate.x-harbor.x,estate.y-harbor.y)<150);
 assert.equal(estate.isLocation,false,'The new small estate is a map object, not a new geographical region');
 assert.equal(estate.capital,false);
 assert.equal(harbor.isLocation,true);
 assert.deepEqual(harbor.linkedLocationIds,['location-raft-estate',CARETAKER,'aderics-repose','ferry-keel-harbor']);
 assert.ok(!harbor.linkedLocationIds.includes('the-headlands'),'The cape stays a separate geographical holding');
 assert.deepEqual(estate.objects.map(object=>object.id),['object-raft-provision-yard','object-raft-hunting-lodge']);
 for(const object of estate.objects){
  assert.equal(effectiveFaction(estate,object),RAFT);
  assert.equal(object.rules.activation,'ownership');
  assert.equal(object.rules.appliesTo,'all-members');
  assert.equal(object.rules.stacking,'additive');
  assert.equal(object.rules.bonusValue,1);
  assert.deepEqual(object.modifiers.map(modifier=>modifier.kind),['bonus']);
 }
 assert.equal(data.locations.length,86);
 assert.equal(data.factions.length,16);
 assert.equal(data.locations.reduce((total,location)=>total+location.objects.length,0),98);
 assert.equal(data.meta.authorScenarioPublication.additionalPins,19);
 assert.deepEqual(data,read('publication-v6.json'));
});

test('Raft hunting and capital food supply face an ordered self-funded sawmill, not completed deforestation',()=>{
 const data=read('atlas.json'),house=data.factions.find(faction=>faction.id===RAFT);
 const harbor=place(data,'keel-harbor'),estate=place(data,'location-raft-estate'),cape=place(data,'the-headlands');
 assert.match(house.description,/продовольств|припас/i);
 assert.match(house.description,/столиц/i);
 assert.match(house.description,/охот|ловч/i);
 assert.match(house.description,/Стены Седогрива/);
 assert.match(house.description,/обязали|предписан/i);
 assert.match(house.description,/лесопилк/i);
 assert.match(house.description,/свои средства|собственный сч[её]т/i);
 assert.match(harbor.description,/Дом[\p{L}\s]*Рафт/iu);
 assert.match(harbor.description,/продовольств|припас/i);
 assert.match(harbor.description,/столиц/i);
 assert.match(estate.description,/ловч|охот/i);
 assert.match(cape.description,/лес/iu);
 assert.match(cape.description,/охот|ловч/i);
 assert.match(cape.description,/пока|ещ[её]|сейчас/i);
 assert.match(cape.description,/вскоре|предстоит|предписан|планир/i);
 assert.match(cape.description,/лесопилк|вырубк/i);
 assert.equal(cape.type,'forest');
 assert.equal(cape.isLocation,true);
 assert.equal(house.provenance.authorScenario.canonicalEvidence,false);
 assert.equal(cape.provenance.authorScenario.raftForestry.sawmillStatus,'ordered-not-built');
 assert.equal(cape.provenance.authorScenario.raftForestry.funding,'house-own-funds');
 assert.equal(cape.provenance.authorScenario.raftForestry.forestStatus,'standing-hunting-ground');
 assert.ok(!cape.objects.some(object=>object.type==='lumbermill'),'Do not create an already-working sawmill before it is built');
 assert.ok(!data.locations.some(location=>location.faction===RAFT&&location.type==='lumbermill'));
});

test('Raft has a distinct authored device packaged in the unchanged shared shield',()=>{
 const data=read('atlas.json'),house=data.factions.find(faction=>faction.id===RAFT);
 assert.equal(house.heraldry?.symbol,'assets/ui/factions/raft-device.svg');
 assert.equal(house.heraldry.origin,'author');
 const manifest=JSON.parse(fs.readFileSync(new URL('../assets/runtime-manifest.json',import.meta.url),'utf8'));
 assert.ok(manifest.includes(house.heraldry.symbol));
 const svg=fs.readFileSync(new URL('../'+house.heraldry.symbol,import.meta.url),'utf8');
 assert.match(svg,/viewBox="0 0 40 44"/);
 assert.doesNotMatch(svg,/<script|<foreignObject|\son\w+=|href=/i);
 const renderer=fs.readFileSync(new URL('../assets/js/heraldry.mjs',import.meta.url),'utf8');
 assert.match(renderer,/M1 1H59V46\.4L30 71 1 46\.4Z/);
});
