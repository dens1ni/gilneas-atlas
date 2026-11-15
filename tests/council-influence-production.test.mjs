import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {normalizeData} from '../assets/js/model.mjs';
const root=new URL('../',import.meta.url);

test('every existing Council person adopts reviewed scenario influence without changing the historic baseline',async()=>{
  const data=JSON.parse(await readFile(new URL('assets/data/atlas.json',root),'utf8'));
  const proof=JSON.parse(await readFile(new URL('docs/council-influence-seed.json',root),'utf8'));
  assert.equal(proof.people.length,proof.personCount);
  assert.equal(new Set(proof.people.map(person=>person.refId)).size,proof.personCount);
  const members=new Map(data.royalCouncil.members.map(member=>[member.id,member]));
  for(const person of proof.people){
    const member=members.get(person.memberId);
    assert.ok(member,person.memberId);assert.equal(member.refId,person.refId);
    assert.deepEqual(member.influence,person.influence,person.refId+' scenario score must be adopted, not remain in a scratch file');
  }
  assert.ok(data.royalCouncil.influence);
  assert.deepEqual(normalizeData(data),data);
});
