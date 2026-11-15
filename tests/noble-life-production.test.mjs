import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {normalizeData} from '../assets/js/model.mjs';
const root=new URL('../',import.meta.url);
const read=async path=>JSON.parse(await readFile(new URL(path,root),'utf8'));

test('every original named noble has the verified historical status and exact traceable evidence',async()=>{
  const data=await read('assets/data/atlas.json'),proof=await read('docs/noble-life-status.json');
  assert.equal(proof.records.length,proof.count);
  assert.equal(new Set(proof.records.map(record=>record.nobleId)).size,proof.count);
  const sources=new Map(data.sources.map(source=>[source.id,source]));
  for(const record of proof.records){
    const noble=data.nobles.find(noble=>noble.id===record.nobleId);
    assert.ok(noble,record.nobleId);
    assert.equal(noble.lifeStatus,record.lifeStatus,record.nobleId+' historical life status must reach the production dataset');
    assert.equal(noble.lifeStatusNote,record.note);
    assert.equal(noble.lifeStatusBasis,record.basis);
    assert.deepEqual(noble.fieldSources.lifeStatus,record.sourceIds);
    for(const id of record.sourceIds)assert.ok(sources.has(id),record.nobleId+': '+id);
    for(const evidence of record.evidence){
      const bytes=await readFile(new URL(evidence.evidenceFile,root));
      assert.equal(createHash('sha256').update(bytes).digest('hex'),evidence.evidenceSha256);
      assert.ok(bytes.toString('utf8').includes(evidence.quote),evidence.evidenceFile);
    }
  }
  assert.deepEqual(normalizeData(data),data);
});
