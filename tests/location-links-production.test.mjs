import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {normalizeData} from '../assets/js/model.mjs';
const root=new URL('../',import.meta.url);
const read=async path=>JSON.parse(await readFile(new URL(path,root),'utf8'));

test('all audited location-container flags and exact canonical references reach production without copying points',async()=>{
  const data=await read('assets/data/publication-v5.json'),proof=await read('docs/location-links-review.json'),before=await read('assets/data/publication-v4.json');
  assert.equal(proof.records.length,proof.auditedCount);
  assert.deepEqual(proof.records.map(row=>row.id),before.locations.map(row=>row.id));
  assert.deepEqual(data.locations.map(row=>row.id),before.locations.map(row=>row.id));
  for(const original of before.locations){
    const actual=data.locations.find(row=>row.id===original.id),review=proof.records.find(row=>row.id===original.id);
    assert.equal(actual.isLocation,review.isLocation,original.id);
    assert.deepEqual(actual.linkedLocationIds,review.linkedLocationIds,original.id);
    for(const [key,value] of Object.entries(original))assert.deepEqual(actual[key],value,original.id+'.'+key);
  }
  assert.deepEqual(data.territories,before.territories);
  assert.deepEqual(normalizeData(data),data);
});
