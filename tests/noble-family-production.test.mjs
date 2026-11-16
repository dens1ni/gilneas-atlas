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

test('every admitted census identity is stored once with its exact live Council person',async()=>{
  const data=await read('assets/data/atlas.json'),census=await read('docs/noble-family-census.json');
  assert.ok(census.additions.length>0);
  assert.equal(census.additions.length,9);
  assert.equal(data.nobles.length,26);
  assert.equal(data.royalCouncil.members.length,33);
  assert.equal(new Set(data.nobles.map(noble=>noble.id)).size,data.nobles.length);
  assert.equal(new Set(data.royalCouncil.members.map(member=>member.id)).size,data.royalCouncil.members.length);
  assert.equal(new Set(data.royalCouncil.members.map(member=>`${member.kind}:${member.refId}`)).size,data.royalCouncil.members.length);
  for(const noble of data.nobles)assert.equal(data.royalCouncil.members.filter(member=>member.kind==='person'&&member.refId===noble.id).length,1,noble.id+' has exactly one live Council person');
  for(const addition of census.additions){
    const noble=data.nobles.find(noble=>noble.id===addition.noble.id);
    assert.ok(noble,addition.noble.id);
    assert.deepEqual(noble,addition.noble,addition.noble.id+' must adopt the complete reviewed record, not a name-only placeholder');
    const seats=data.royalCouncil.members.filter(member=>member.kind==='person'&&member.refId===noble.id);
    assert.equal(seats.length,1,noble.id);
    assert.deepEqual(seats[0],addition.council,noble.id+' must retain era, party, uncertainty and scenario influence provenance');
  }
  assert.deepEqual(normalizeData(data),data);
});

test('immutable publication v5 preserves every original v4 noble field, location field and border',async()=>{
  const data=await read('assets/data/publication-v5.json');
  const baseline=await read('assets/data/publication-v4.json');
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

test('current v6 nobles equal publication v5 except exact approved Walden, Harford and Candren authorship',async()=>{
  const data=await read('assets/data/atlas.json'),baseline=await read('assets/data/publication-v5.json');
  const approved=await read('tests/fixtures/harford-candren-approved-nobles.json');
  assert.deepEqual(Object.keys(approved),['noble-candren','noble-harford']);
  assert.equal(baseline.nobles.length,26);
  assert.equal(data.nobles.length,26);
  assert.deepEqual(data.nobles.map(noble=>noble.id).sort(),baseline.nobles.map(noble=>noble.id).sort());
  for(const original of baseline.nobles){
    const actual=data.nobles.find(noble=>noble.id===original.id);
    const expected=original.id==='noble-walden'?{
      ...original,
      name:'Лорд Вальден',
      shortDescription:'Прибрежный лорд и покровитель магических изысканий; его собственная арканистика остаётся предметом слухов.',
      description:'Лорд Вальден ведает восточными владениями своего дома и проявляет необычный интерес к магическим знаниям. Он собирает арканные книги и приглашает ко двору королевских магов; ходят слухи, что и сам лорд практикует магию Порядка — арканистику. По его распоряжению Южный маяк оборудован для магических изысканий и получил имя Маяк Звёздного Порядка: здесь находят общий стол и приют чародеи, прежде работавшие по всему Гилнеасу порознь.',
      holdingsNote:'Предел бури, поместье дома Вальден, Маяк Звёздного Порядка и Ипподром.',
      sources:[...original.sources,'source-lore-walden-wowpedia-api','source-lore-walden-house-wowpedia-api'],
      provenance:{
        ...original.provenance,
        sources:[...original.provenance.sources,'source-lore-walden-wowpedia-api','source-lore-walden-house-wowpedia-api'],
        authorScenario:{
          currentManagement:'explicit user request; canonical early life/title unproved',
          holdings:'scenario cadastral assignment',
          politics:'no inferred wall stance, royalist affiliation or canonical appointment',
          arcanePatronage:{
            basis:'explicit-user-authorship',
            canonicalEvidence:false,
            personalPractice:'rumor',
            royalMageNetwork:'scattered local royal mages drawn to the lighthouse; not a newly founded kingdom-wide order'
          }
        }
      }
    }:Object.hasOwn(approved,original.id)?approved[original.id]:original;
    assert.deepEqual(actual,expected,original.id+' must retain the complete v5 record except exact approved authored fields');
  }
});
