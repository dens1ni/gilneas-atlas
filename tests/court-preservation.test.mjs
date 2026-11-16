import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url);

test('court revision preserves every existing map point, owner, source identity and manual-border baseline',async()=>{
  const previous=JSON.parse(await readFile(new URL('assets/data/publication-v3.json',root),'utf8'));
  const actual=JSON.parse(await readFile(new URL('assets/data/publication-v5.json',root),'utf8'));
  assert.deepEqual(actual.locations.map(record=>record.id),previous.locations.map(record=>record.id),'No extra, removed or reordered map records');
  for(const original of previous.locations){
    const current=actual.locations.find(record=>record.id===original.id);
    for(const [key,value] of Object.entries(original))assert.deepEqual(current[key],value,original.id+'.'+key+' map field stays literal');
    assert.ok(Object.keys(current).every(key=>Object.hasOwn(original,key)||['isLocation','linkedLocationIds'].includes(key)),original.id+' only receives the requested navigation fields');
  }
  assert.deepEqual(actual.territories,previous.territories,'Do not regenerate scenario or author geography');
  for(const original of previous.nobles){
    const current=actual.nobles.find(record=>record.id===original.id);
    assert.ok(current,'Preserve original person '+original.id);
    for(const [key,value] of Object.entries(original)){
      if(key==='fieldSources')for(const [field,refs] of Object.entries(value))assert.deepEqual(current[key][field],refs,original.id+'.fieldSources.'+field);
      else assert.deepEqual(current[key],value,original.id+'.'+key+' biography field stays literal');
    }
    assert.ok(Object.keys(current).every(key=>Object.hasOwn(original,key)||['lifeStatus','lifeStatusNote','lifeStatusBasis'].includes(key)),original.id+' only receives the requested status fields');
  }
  for(const field of ['width','height','image','mist','inactiveMask','mapRevision','mapRegistration','homeBounds','gilneasHeraldry'])assert.deepEqual(actual.meta[field],previous.meta[field],field);
  const stripHeraldry=record=>{const {heraldry,...rest}=record;return rest;};
  assert.deepEqual(actual.factions.map(stripHeraldry),previous.factions,'Heraldry must not alter rulers or vasallage');
  const sources=new Map(actual.sources.map(source=>[source.id,source]));
  for(const source of previous.sources)assert.deepEqual(sources.get(source.id),source,'Preserve exact source '+JSON.stringify(source.id));
});
