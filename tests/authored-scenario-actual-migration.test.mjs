import test from 'node:test';
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import fs from 'node:fs';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';
import {normalizeData,serializeSnapshot,deserializeSnapshot} from '../assets/js/model.mjs';
const load = name => JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url)));
const old=load('publication-v5.json'),seed=load('publication-author-v5.json');
const approvedEvent=JSON.parse(fs.readFileSync(new URL('./fixtures/crown-order-event.json',import.meta.url),'utf8'));
const expectedTrack=author=>({...author,baseValue:0,value:10,events:[approvedEvent]});
test('pristine v5 and exact author ZIP reconcile to approved 86-pin content while respecting prior grid presence',()=>{
 const release=load('publication-v6.json');
 for(const source of [old,seed]){
  const draft=structuredClone(source),before=structuredClone(draft);
  const result=normalizeData(reconcileDraftPublication(draft,release,old,seed));
  assert.deepEqual(draft,before);
  const expected=structuredClone(release);
  if(source===old)delete expected.territoryGrid;
  for(const key of Object.keys(expected))assert.ok(isDeepStrictEqual(result[key],expected[key]),`Approved ${key} content for ${source===old?'pristine v5':'author ZIP'}`);
  assert.deepEqual(Object.keys(result).sort(),Object.keys(expected).sort());
  assert.equal(result.locations.length,86);
  assert.equal(result.locations.reduce((n,place)=>n+place.objects.length,0),98);
  if(source===seed){
   assert.ok(isDeepStrictEqual(result.territoryGrid,release.territoryGrid), 'Untouched historical grid adopts the approved full-realm redraw');
   assert.equal(result.territoryGrid.migration.method,'author-full-realm-layout');
  }else assert.equal(Object.hasOwn(result,'territoryGrid'),false,'L01 seed prior presence forbids first adoption into gridless v5');
  assert.deepEqual(result.territories,[]);
  assert.deepEqual(result.meta.wallConstruction,expectedTrack(seed.meta.wallConstruction));
  assert.ok(isDeepStrictEqual(deserializeSnapshot(serializeSnapshot(result)),result),'Complete snapshot round-trip');
  assert.ok(isDeepStrictEqual(reconcileDraftPublication(result,release,release,seed),result),'Complete migration idempotence');
 }
});
test('actual author ZIP custom moved UUID and text remain literal instead of acquiring reviewed ownership',()=>{
 const release=load('publication-v6.json'),draft=structuredClone(seed);
 const id='location-76bf7c1a-fcd2-4dfc-9013-26b909b4732f';
 const location=draft.locations.find(place=>place.id===id);
 location.x+=1;location.description='  Личный текст владельца  ';
 const before=structuredClone(location);
 const result=normalizeData(reconcileDraftPublication(draft,release,old,seed));
 assert.deepEqual(result.locations.find(place=>place.id===id),before);
 const harbor=result.locations.find(place=>place.id==='duskhaven');
 assert.ok(!harbor.linkedLocationIds.includes(id));
 assert.deepEqual(result.meta.wallConstruction,expectedTrack(draft.meta.wallConstruction),'A custom location does not make an untouched Wall ledger custom');
 assert.ok(isDeepStrictEqual(result.territoryGrid,release.territoryGrid), 'A custom location does not make an untouched historical grid custom');
 assert.equal(result.territoryGrid.migration.method,'author-full-realm-layout');
 assert.deepEqual(result.territories,[]);
});
