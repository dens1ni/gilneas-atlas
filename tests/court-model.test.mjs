import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeData,saveDraft} from '../assets/js/model.mjs';
const fixture=()=>({version:1,meta:{width:100,height:100},factions:[{id:'house',name:'Дом',color:'#123456',parent:null}],locations:[{id:'town',name:'Место',type:'building',x:10,y:20,faction:'house',owner:'',description:'',objects:[]}],nobles:[],sources:[],territories:[]});

test('optional faction heraldry validates readable fields before storage without rewriting custom symbols',()=>{
  for(const invalid of [null,[],false,'crest',{}, {symbol:{}}, {symbol:'assets/ui/custom.svg',edge:[]}, {symbol:'assets/ui/custom.svg',device:'#xxzz00'}]){
    const value=fixture();value.factions[0].heraldry=invalid;
    let calls=0;const storage={setItem(){calls++;}};
    assert.throws(()=>saveDraft(storage,value),/герб|heraldry/i);
    assert.equal(calls,0);
  }
  const value=fixture();value.factions[0].heraldry={symbol:'assets/ui/custom.svg',edge:'#65707b',device:'#9aa8b6',origin:'author',note:'  Авторский символ  '};
  assert.deepEqual(normalizeData(value).factions[0].heraldry,value.factions[0].heraldry);
});

test('farm objects are valid full-snapshot records and retain modifiers',()=>{
  const value=fixture();value.locations[0].objects.push({id:'farm',type:'farm',name:'  Авторская ферма  ',owner:'',description:'  Поля  ',modifiers:[{id:'farm-bonus',kind:'bonus',text:'+5 снабжение'}]});
  const result=normalizeData(value);
  assert.deepEqual(result.locations[0].objects,value.locations[0].objects);
});

test('malformed council assignments fail before any snapshot persistence',()=>{
  for(const invalid of [null,[],{}, {version:1,members:[{id:'seat',kind:'faction',refId:'missing',party:'neutral',stance:'unknown',advisor:false,active:true,note:''}]}, {version:1,members:[{id:'seat',kind:'person',name:'',party:'neutral',stance:'unknown',advisor:false,active:true,note:''}]}]){
    const value=fixture();value.royalCouncil=invalid;let writes=0;
    assert.throws(()=>saveDraft({setItem(){writes++;}},value),/Совет|ссылка|имя/i);
    assert.equal(writes,0);
  }
  const value=fixture();value.royalCouncil={version:1,members:[{id:'seat',kind:'faction',refId:'house',party:'royalists',stance:'support',advisor:false,active:true,note:'  Мой сценарий  '}]};
  assert.deepEqual(normalizeData(value).royalCouncil,value.royalCouncil);
});

test('wall event inputs and cached progress validate before storage while legacy author value remains exact',()=>{
  for(const invalid of [{value:10,max:100,events:{}},{value:25,max:100,baseValue:10,events:[{id:'event',name:'',delta:15}]},{value:10,max:100,baseValue:10,events:[{id:'event',name:'Событие',delta:15}]}]){
    const value=fixture();value.meta.wallConstruction=invalid;let writes=0;
    assert.throws(()=>saveDraft({setItem(){writes++;}},value),/стен|событи|прогресс/i);
    assert.equal(writes,0);
  }
  const value=fixture();value.meta.wallConstruction={value:43,max:91,note:'  Авторский этап  '};
  assert.deepEqual(normalizeData(value).meta.wallConstruction,value.meta.wallConstruction);
});

test('council references block deletion of an assigned house before live or storage data can diverge',async()=>{
  const {deleteFaction}=await import('../assets/js/model.mjs');
  const value=fixture();value.factions.push({id:'guest-house',name:'Свободный дом',color:'#678abc',parent:null});
  value.royalCouncil={version:1,members:[{id:'house-seat',kind:'faction',refId:'guest-house',party:'neutral',stance:'unknown',advisor:false,active:true,note:''}]};
  const before=structuredClone(value);
  assert.throws(()=>deleteFaction(value,'guest-house'),/используется/i);
  assert.deepEqual(value,before);
});
