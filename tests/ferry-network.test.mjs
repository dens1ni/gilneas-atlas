import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {isDeepStrictEqual} from 'node:util';
import {OBJECT_TYPE_IDS,TYPE_DEFINITIONS,typeName} from '../assets/js/object-types.mjs';
import {normalizeData,serializeSnapshot,deserializeSnapshot,effectiveFaction,removeLocation,updateLocation} from '../assets/js/model.mjs';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';

const load=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const FERRIES=['ferry-duskhaven','ferry-keel-harbor','ferry-stormglen'];

test('ferrymen have their own immutable boat glyph and Russian type, not an owner shield',()=>{
 assert.ok(OBJECT_TYPE_IDS.includes('ferry'),'Add a dedicated ferry type for the requested special markers');
 const definition=TYPE_DEFINITIONS.find(record=>record.id==='ferry');
 assert.equal(typeName('ferry'),'Паромная пристань');
 assert.ok(Object.isFrozen(definition));
 assert.notEqual(definition.path,TYPE_DEFINITIONS.find(record=>record.id==='harbor').path);
 assert.notEqual(definition.path,TYPE_DEFINITIONS.find(record=>record.id==='building').path);
 assert.match(definition.path,/^M/);
 assert.doesNotMatch(definition.path,/[<>]/);
});

test('three separate ferryman markers sit on the photographed dock tips and retain canonical harbor links',()=>{
 const data=load('atlas.json');
 const specs=[['ferry-duskhaven','duskhaven','gilneas','',548,3414],['ferry-keel-harbor','keel-harbor','raft','Дом Рафт',1203,2747],['ferry-stormglen','stormglen','ashbury','Барон Эшбери',1891,3984]];
 assert.equal(data.locations.filter(record=>record.type==='ferry').length,3,'Add exactly three requested ferryman dock markers');
 for(const [id,parentId,faction,owner,x,y] of specs){
  const dock=data.locations.find(record=>record.id===id),parent=data.locations.find(record=>record.id===parentId);
  assert.ok(dock,id);assert.equal(dock.type,'ferry');assert.match(dock.name,/Паромщик/);
  assert.equal(dock.isLocation,false);assert.equal(dock.capital,false);
  assert.deepEqual([dock.x,dock.y],[x,y]);assert.equal(dock.faction,faction);assert.equal(dock.owner,owner);
  assert.ok(parent.linkedLocationIds.includes(id),'Keep an exact geographical reference to the new dock');
  assert.equal(dock.provenance.authorScenario.basis,'explicit-user-authorship');assert.equal(dock.provenance.authorScenario.canonicalEvidence,false);
  assert.ok(!Object.hasOwn(dock,'amount'));
  assert.equal(dock.objects.length,1,'One modest ferry service object, not copied effects from the harbor');
  const service=dock.objects[0];assert.equal(service.type,'ferry');assert.equal(service.owner,owner);
  assert.equal(service.rules.activation,'ownership');assert.equal(service.rules.appliesTo,'all-members');assert.equal(service.rules.stacking,'additive');assert.equal(service.rules.bonusValue,1);
  assert.equal(service.modifiers.length,1);assert.equal(service.modifiers[0].kind,'bonus');assert.equal(service.modifiers[0].text,'+1 к проверкам с водным транспортом всей фракции.');
 }
 assert.deepEqual(data,load('publication-v6.json'));
});

test('two preserved polylines connect all three canonical ferry tips around the real coast',()=>{
 const data=load('atlas.json'),network=data.meta.ferryNetwork;
 assert.ok(network,'Persist the requested ferry route geometry in the full snapshot');
 assert.equal(network.image,data.meta.image);assert.equal(network.mapRevision,data.meta.mapRevision);
 assert.equal(network.width,data.meta.width);assert.equal(network.height,data.meta.height);
 assert.equal(network.routes.length,2);
 const refs=new Set();
 for(const route of network.routes){
  const from=data.locations.find(l=>l.id===route.fromLocationId),to=data.locations.find(l=>l.id===route.toLocationId);
  assert.ok(from&&to);assert.equal(from.type,'ferry');assert.equal(to.type,'ferry');assert.notEqual(from.id,to.id);
  refs.add(from.id);refs.add(to.id);assert.deepEqual(route.points[0],[from.x,from.y]);assert.deepEqual(route.points.at(-1),[to.x,to.y]);
  assert.ok(route.points.length>=3&&route.points.length<=4096);
  for(const point of route.points)assert.ok(point.length===2&&point.every(Number.isFinite));
 }
 assert.deepEqual([...refs].sort(),[...FERRIES].sort());
 assert.deepEqual(normalizeData(data),data);assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)),data);
});

test('malformed route metadata is rejected before complete snapshot replacement and its IDs share the model namespace',()=>{
 const data=load('atlas.json'),original=serializeSnapshot(data);
 const invalid=structuredClone(data);invalid.meta.ferryNetwork.routes[0].points[1][0]='1200';
 assert.throws(()=>normalizeData(invalid),/паром|маршрут|координат/i,'Do not persist an invalid renderer-consumed route');
 const collision=structuredClone(data);collision.meta.ferryNetwork.routes[0].id=collision.locations[0].objects[0].id;
 assert.throws(()=>normalizeData(collision),/Повтор ID/,'Route IDs must use the whole model namespace');
 const missing=structuredClone(data);missing.meta.ferryNetwork.routes[0].fromLocationId='missing-ferry';
 assert.throws(()=>normalizeData(missing),/meta\.ferryNetwork\.routes\[0\]\.fromLocationId: ID missing-ferry не найден/);
 assert.equal(serializeSnapshot(data),original);
});

test('deleting one dock removes only its dependent routes while moving a dock retains original geometry',()=>{
 const data=load('atlas.json');
 const removed=removeLocation(data,'ferry-keel-harbor');
 assert.deepEqual(removed.meta.ferryNetwork.routes.map(route=>route.id),['ferry-route-duskhaven-stormglen'],'Remove the vanished pier’s dependent route, not the whole network');
 assert.ok(!removed.locations.find(l=>l.id==='keel-harbor').linkedLocationIds.includes('ferry-keel-harbor'));
 assert.deepEqual(removed.locations.filter(l=>l.type==='ferry').map(l=>l.id),['ferry-duskhaven','ferry-stormglen']);
 const moved=updateLocation(data,'ferry-keel-harbor',{x:1205});
 assert.deepEqual(moved.meta.ferryNetwork,data.meta.ferryNetwork,'A changed pin does not authorize a new path across unknown terrain');
 assert.deepEqual(data,load('atlas.json'));
});

test('the real old drafts adopt ferry routes without changes to raw inputs and preserve custom/deleted network choices',()=>{
 const release=load('atlas.json'),old=load('publication-v5.json'),seed=load('publication-author-v5.json');
 for(const source of [old,seed]){
  const draft=structuredClone(source),result=normalizeData(reconcileDraftPublication(draft,release,old,seed));
  const expected=structuredClone(release);if(source===old)delete expected.territoryGrid;
  for(const key of Object.keys(expected))assert.ok(isDeepStrictEqual(result[key],expected[key]),`Approved ${key} content`);
  assert.deepEqual(Object.keys(result).sort(),Object.keys(expected).sort());
  assert.equal(Object.hasOwn(result,'territoryGrid'),source===seed,'L01 preserves grid absence when the author seed had a grid');
  assert.deepEqual(draft,source);
 }
 const custom=structuredClone(seed);custom.meta.ferryNetwork={...structuredClone(release.meta.ferryNetwork),routes:[],authorExtension:{literal:'  Пользовательская линия  ',sources:['not-a-source']}};
 const updated=normalizeData(reconcileDraftPublication(custom,release,old,seed));assert.deepEqual(updated.meta.ferryNetwork,custom.meta.ferryNetwork);
 const future=structuredClone(release);future.meta.publicationRevision='ferry-test-future';
 const deleted=structuredClone(release);delete deleted.meta.ferryNetwork;
 assert.ok(!Object.hasOwn(reconcileDraftPublication(deleted,future,release,seed).meta,'ferryNetwork'));
});

test('first ferry adoption filters routes to an unrelated author dock rather than making invalid references',()=>{
 const release=load('atlas.json'),old=load('publication-v5.json'),seed=load('publication-author-v5.json');
 const draft=structuredClone(seed);
 const custom={id:'ferry-keel-harbor',name:'  Авторская чужая пристань  ',type:'landmark',x:700,y:3200,faction:'gilneas',owner:'',description:'  Не заменять  ',objects:[]};
 draft.locations.push(custom);const original=structuredClone(draft);
 const result=normalizeData(reconcileDraftPublication(draft,release,old,seed));
 assert.deepEqual(result.locations.find(l=>l.id===custom.id),custom);
 assert.deepEqual(result.meta.ferryNetwork.routes.map(route=>route.id),['ferry-route-duskhaven-stormglen'],'No adopted route may bind an unrelated author pin');
 assert.deepEqual(draft,original);
});

test('new ferry-route IDs preflight against author nested object IDs before any migration changes',()=>{
 const release=load('atlas.json'),old=load('publication-v5.json'),seed=load('publication-author-v5.json');
 for(const collection of ['objects','sources','council','wall']){
  const draft=structuredClone(seed);
  const id='ferry-route-keel-duskhaven';
  if(collection==='objects')draft.locations[0].objects.push({id,type:'building',name:'Чужой объект',owner:'',description:'',modifiers:[]});
  if(collection==='sources')draft.sources.push({id,title:'Чужой источник',url:'https://example.org/author-evidence'});
  if(collection==='council')draft.royalCouncil.members[0].id=id;
  if(collection==='wall')draft.meta.wallConstruction.events[0].id=id;
  const before=structuredClone(draft);
  assert.throws(()=>reconcileDraftPublication(draft,release,old,seed),/ID conflict/,'Ferry IDs must preflight against '+collection);
  assert.deepEqual(draft,before);
 }
});
