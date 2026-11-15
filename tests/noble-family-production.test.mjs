import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {normalizeData} from '../assets/js/model.mjs';
const root=new URL('../',import.meta.url);
const read=async path=>JSON.parse(await readFile(new URL(path,root),'utf8'));

test('the named Greymane and Crowley relatives exist as canonical people and exact Council references',async()=>{
  const data=await read('assets/data/atlas.json');
  const relatives=[['noble-mia','greymane'],['noble-liam','greymane'],['noble-tess','greymane'],['noble-lorna','crowley']];
  const people=data.royalCouncil.members.filter(member=>member.kind==='person');
  for(const [id,house] of relatives){
    const noble=data.nobles.find(noble=>noble.id===id);
    assert.ok(noble,`Missing named noble relative ${id}: a mention in another person's relations is not a canonical record`);
    assert.equal(noble.house,house);
    assert.ok(['alive','dead','unknown'].includes(noble.lifeStatus),id+' has an era-relative life status');
    assert.ok(noble.sources.length,id+' has exact source evidence');
    const seats=people.filter(member=>member.refId===id);
    assert.equal(seats.length,1,id+' appears exactly once in the Council');
    const member=seats[0];
    assert.ok(['royalists','internationalists','neutral'].includes(member.party));
    assert.ok(['support','oppose','unknown'].includes(member.stance));
    assert.equal(member.advisor,false,'A family relation is not proof of an advisory office');
    assert.equal(member.votingSeat,false,'Family register inclusion does not invent a voting seat');
    for(const field of ['party','kingdom'])assert.ok(Number.isInteger(member.influence[field])&&member.influence[field]>=0&&member.influence[field]<=100);
  }
});

test('every admitted census identity is stored once with a Council person and all existing text is preserved',async()=>{
  const data=await read('assets/data/atlas.json'),census=await read('docs/noble-family-census.json');
  const baseline=await read('assets/data/publication-v4.json');
  assert.ok(census.additions.length>0);
  assert.equal(new Set(data.nobles.map(noble=>noble.id)).size,data.nobles.length);
  for(const addition of census.additions){
    const noble=data.nobles.find(noble=>noble.id===addition.noble.id);
    assert.ok(noble,addition.noble.id);
    assert.deepEqual(noble,addition.noble,addition.noble.id+' must adopt the complete reviewed record, not a name-only placeholder');
    const seats=data.royalCouncil.members.filter(member=>member.kind==='person'&&member.refId===noble.id);
    assert.equal(seats.length,1,noble.id);
    assert.deepEqual(seats[0],addition.council,noble.id+' must retain era, party, uncertainty and scenario influence provenance');
  }
  for(const original of baseline.nobles){
    const actual=data.nobles.find(noble=>noble.id===original.id);
    for(const [key,value] of Object.entries(original)){
      if(key==='fieldSources')for(const [field,refs] of Object.entries(value))assert.deepEqual(actual[key][field],refs,original.id+'.'+key+'.'+field);
      else assert.deepEqual(actual[key],value,original.id+'.'+key+' author field must remain literal');
    }
  }
  for(const original of baseline.locations){
    const actual=data.locations.find(row=>row.id===original.id);
    for(const [key,value] of Object.entries(original))assert.deepEqual(actual[key],value,original.id+'.'+key+' map field stays literal');
  }
  assert.deepEqual(data.territories,baseline.territories,'Family work does not regenerate borders');
  assert.deepEqual(normalizeData(data),data);
});
