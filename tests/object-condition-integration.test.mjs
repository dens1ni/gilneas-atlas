import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {normalizeData,updateLocation,upsertObject,serializeSnapshot,deserializeSnapshot} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
test('destroyed condition accepts only literal booleans and survives immutable complete editor transactions',()=>{
 const data=read('atlas.json');
 for(const field of ['location','object'])for(const invalid of ['true',1,null,[],{}]){
  const draft=structuredClone(data);const record=field==='location'?draft.locations[0]:draft.locations[0].objects[0];record.destroyed=invalid;
  assert.throws(()=>normalizeData(draft),/destroyed|Разрушено|разруш/i,field+' rejects '+JSON.stringify(invalid));
 }
 const location=data.locations.find(l=>l.id==='location-gray-ford-north-burned-house');
 assert.equal(location.destroyed,true);assert.equal(location.objects[0].destroyed,true);
 const updated=updateLocation(data,location.id,{destroyed:false});assert.equal(updated.locations.find(l=>l.id===location.id).destroyed,false);
 assert.equal(data.locations.find(l=>l.id===location.id).destroyed,true);
 const next=upsertObject(updated,location.id,{...location.objects[0],destroyed:false});
 assert.equal(next.locations.find(l=>l.id===location.id).objects[0].destroyed,false);
 assert.deepEqual(deserializeSnapshot(serializeSnapshot(next)),next);
 const untouched=next.locations.find(l=>l.id==='gilneas-city');assert.ok(!Object.hasOwn(untouched,'destroyed'));
 assert.deepEqual(next.territoryGrid,data.territoryGrid);assert.deepEqual(next.meta,data.meta);
 const manifest=JSON.parse(fs.readFileSync(new URL('../assets/runtime-manifest.json',import.meta.url),'utf8'));
 for(const path of ['assets/js/object-condition.mjs','assets/css/object-condition.css'])assert.ok(manifest.includes(path),path);
});
