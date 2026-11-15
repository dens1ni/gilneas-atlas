import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeData,saveDraft,serializeSnapshot,deserializeSnapshot} from '../assets/js/model.mjs';
const snapshot=()=>({version:1,meta:{width:100,height:100},factions:[],locations:[],territories:[],sources:[],nobles:[{id:'  noble  ',name:'  Имя автора  ',lifeStatus:'alive',custom:{literal:[0,'0']}}]});
test('the real model rejects explicit invalid noble life statuses before storage without coercion',()=>{
  for(const status of [null,'Жив','Alive',' alive ',false,0,{},[]]){
    const data=snapshot();data.nobles[0].lifeStatus=status;const before=structuredClone(data),calls=[];
    assert.throws(()=>saveDraft({setItem:(...args)=>calls.push(args)},data),/статус|lifeStatus/i);
    assert.deepEqual(calls,[]);assert.deepEqual(data,before);
  }
});
test('status evidence rejects malformed or unresolved exact source IDs before saving',()=>{
  for(const value of [null,'source',{},0,[1],['missing'],[1,'1']]){
    const data=snapshot();data.nobles[0].fieldSources={lifeStatus:value};
    data.sources=[{id:'1',title:'Авторский источник',url:'https://example.invalid/one'}];
    const before=structuredClone(data),writes=[];
    assert.throws(()=>saveDraft({setItem:(...args)=>writes.push(args)},data),/источник|fieldSources/i);
    assert.deepEqual(writes,[]);assert.deepEqual(data,before);
  }
  const valid=snapshot();valid.sources=[{id:1,title:'Один',url:'https://example.invalid/one'},{id:'1',title:'Другой',url:'https://example.invalid/other'}];
  valid.nobles[0].fieldSources={lifeStatus:[1,'1'],custom:{literal:'  Сохранить  '}};
  assert.deepEqual(normalizeData(valid),valid);
});

test('valid life statuses roundtrip literally and absent legacy status is not seeded on load',()=>{
  for(const status of ['alive','dead','unknown']){const data=snapshot();data.nobles[0].lifeStatus=status;assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)),data);}
  const legacy=snapshot();delete legacy.nobles[0].lifeStatus;assert.deepEqual(normalizeData(legacy),legacy);
});
