import test from 'node:test';
import assert from 'node:assert/strict';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';

const previous=()=>({version:1,meta:{width:100,height:100,publicationRevision:'royal-council-v4'},factions:[{id:'house',name:'Дом',color:'#123456',parent:null}],locations:[],nobles:[{id:'lord',name:'Лорд',house:'house'}],sources:[],territories:[],royalCouncil:{version:1,members:[{id:'seat',kind:'person',refId:'lord',party:'royalists',stance:'unknown',advisor:false,active:true,note:'Первичная заметка'}]}});
const publication=()=>{const data=previous();data.meta.publicationRevision='royal-council-v5';data.royalCouncil.influence={royalists:250,internationalists:175};data.royalCouncil.members[0].influence={party:80,kingdom:60};return data;};

test('new influence fields enrich an unchanged assignment even when the author edited its note',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  draft.royalCouncil.members[0].note='  Своя заметка  ';draft.royalCouncil.extension={kept:true};
  const result=reconcileDraftPublication(draft,release,before);
  assert.deepEqual(result.royalCouncil.members[0].influence,{party:80,kingdom:60});
  assert.equal(result.royalCouncil.members[0].note,'  Своя заметка  ');
  assert.deepEqual(result.royalCouncil.extension,{kept:true});
  assert.deepEqual(result.royalCouncil.influence,{royalists:250,internationalists:175});
  assert.equal(Object.hasOwn(draft.royalCouncil.members[0],'influence'),false);
});

test('custom party balances and person ratings remain literal after a publication update',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  draft.royalCouncil.influence={royalists:0,internationalists:1234,authorNote:'  Сохранить  '};
  draft.royalCouncil.members[0].influence={party:0,kingdom:25,author:{custom:true}};
  const frozen=structuredClone(draft),result=reconcileDraftPublication(draft,release,before);
  assert.deepEqual(result.royalCouncil,draft.royalCouncil);assert.deepEqual(draft,frozen);
});

test('an author-changed political affiliation is never seeded with another party rating',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();draft.royalCouncil.members[0].party='internationalists';
  const result=reconcileDraftPublication(draft,release,before);
  assert.equal(result.royalCouncil.members[0].party,'internationalists');
  assert.equal(Object.hasOwn(result.royalCouncil.members[0],'influence'),false);
});

test('deleted Council people stay deleted and new author people never receive guessed stats',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  draft.royalCouncil.members=[{id:'author-person',kind:'person',name:'  Свой советник  ',party:'neutral',stance:'unknown',advisor:false,active:true,note:'  Не гадать  '}];
  const result=reconcileDraftPublication(draft,release,before);
  assert.deepEqual(result.royalCouncil.members,draft.royalCouncil.members);
  assert.deepEqual(reconcileDraftPublication(result,release,before),result);
});
