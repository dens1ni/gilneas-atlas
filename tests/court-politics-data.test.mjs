import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {normalizeData} from '../assets/js/model.mjs';

const root=new URL('../',import.meta.url);
const load=async path=>JSON.parse(await readFile(new URL(path,root),'utf8'));

test('the court publication covers every existing person and all seven houses without appointing historical predecessors',async()=>{
  const data=await load('assets/data/atlas.json');
  const previous=await load('assets/data/publication-v3.json');
  assert.ok(data.royalCouncil,'The researched Royal Council must be published, not remain a scratch-only fixture');
  const members=data.royalCouncil.members;
  const census=await load('docs/noble-family-census.json');
  const expectedNewIds=census.additions.map(addition=>addition.noble.id);
  assert.equal(members.length,previous.nobles.length+expectedNewIds.length+7);
  assert.equal(new Set(members.map(member=>member.id)).size,members.length);
  const people=members.filter(member=>member.kind==='person');
  const houses=members.filter(member=>member.kind==='faction');
  assert.deepEqual(people.map(member=>member.refId).sort(),[...previous.nobles.map(noble=>noble.id),...expectedNewIds].sort());
  const originalPeople=people.filter(member=>previous.nobles.some(noble=>noble.id===member.refId));
  assert.deepEqual(houses.map(member=>member.refId).sort(),['greymane','crowley','silverlaine','godfrey','ashbury','marley','walden'].sort());
  const person=new Map(people.map(member=>[member.refId,member]));
  for(const [id,party,stance] of [['noble-genn','royalists','support'],['noble-darius','internationalists','oppose'],['noble-godfrey','royalists','support'],['noble-ashbury','royalists','unknown']]){
    assert.equal(person.get(id).party,party,id);
    assert.equal(person.get(id).stance,stance,id);
  }
  assert.deepEqual(people.filter(member=>member.advisor).map(member=>member.refId).sort(),['noble-darius','noble-godfrey','noble-ashbury'].sort());
  assert.deepEqual(originalPeople.filter(member=>!member.active).map(member=>member.refId).sort(),['noble-archibald','noble-ashbury-first','noble-aderic'].sort());
  for(const addition of census.additions){
    const member=person.get(addition.noble.id);
    assert.deepEqual(member,addition.council);
    assert.equal(member.advisor,false);
    assert.equal(member.votingSeat,false);
  }
  for(const member of members){
    assert.ok(member.sources.length,member.id+' has a traceable source');
    assert.equal(typeof member.note,'string');
    if(member.potentialAlly)assert.equal(member.votingSeat,false,'A possible ally is not an automatically appointed voter');
  }
  for(const id of ['noble-marley','noble-silverlaine','noble-walden']){
    assert.equal(person.get(id).party,'neutral',id);
    assert.equal(person.get(id).stance,'unknown',id);
    assert.equal(person.get(id).advisor,false,id);
  }
  assert.deepEqual(data.meta.wallConstruction,previous.meta.wallConstruction,'No invented inaugural construction events');
  assert.equal(data.meta.publicationRevision,'royal-council-v5');
  assert.deepEqual(normalizeData(data),data,'The published full snapshot is already valid without normalization loss');
});

test('every published faction adopts its exact reviewed device and the runtime ZIP contains it',async()=>{
  const data=await load('assets/data/atlas.json');
  const proof=await load('docs/faction-heraldry.json');
  const manifest=await load('assets/runtime-manifest.json');
  assert.equal(proof.factions.length,10);
  for(const record of proof.factions){
    const faction=data.factions.find(faction=>faction.id===record.id);
    assert.deepEqual(faction.heraldry,record.heraldry,'Missing reviewed heraldry for '+record.id);
    assert.ok(manifest.includes(record.heraldry.symbol),'Missing runtime device for '+record.id);
  }
});
