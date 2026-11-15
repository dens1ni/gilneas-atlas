import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeData, updateLocation, removeLocation, serializeSnapshot, deserializeSnapshot, saveDraft } from '../assets/js/model.mjs';

function snapshot() {
  return { version:1, meta:{width:100,height:100,author:{note:'  Не менять  '}},
    factions:[{id:'district-house',name:'Дом квартала',color:'#112233',parent:null},{id:'prison-house',name:'Дом тюрьмы',color:'#445566',parent:null}],
    locations:[
      {id:'district',name:'Тестовый квартал',type:'district',x:10,y:10,faction:'district-house',owner:'',description:'  Исходный квартал  ',objects:[],isLocation:true,linkedLocationIds:['prison']},
      {id:'prison',name:'Тестовая тюрьма',type:'fortress',x:20,y:20,faction:'prison-house',owner:'  Хранитель  ',description:'  Исходная тюрьма  ',objects:[{id:'supply',name:'Снабжение',type:'resource',description:'  Объяснение эффекта  ',owner:'',amount:0,modifiers:[{id:'supplied',kind:'bonus',text:'  Бонус тюрьмы  '}],custom:{keep:true}}]},
      {id:'other',name:'Другая метка',type:'settlement',x:30,y:30,faction:null,owner:'',description:'',objects:[],custom:{literal:[0,'0']}},
    ], territories:[],nobles:[],sources:[],custom:{untouched:true} };
}
function frozen(value) { if(value&&typeof value==='object'){Object.values(value).forEach(frozen);Object.freeze(value);} return value; }

test('normalization rejects dangling canonical location links before any storage write',()=>{
  const data=snapshot(); data.locations[0].linkedLocationIds=['missing']; const before=structuredClone(data);
  const calls=[]; const storage={setItem:(...args)=>calls.push(args)};
  assert.throws(()=>saveDraft(storage,frozen(data)),/Неизвестн.*метк|ссылк.*не найден|Локация.*не найдена/i);
  assert.deepEqual(calls,[]); assert.deepEqual(data,before);
});

test('location flags and links reject malformed values, self/cycles, duplicates and inline-object targets',()=>{
  for(const [field,value] of [['isLocation','true'],['isLocation',null],['linkedLocationIds','prison'],['linkedLocationIds',null],['linkedLocationIds',[1]],['linkedLocationIds',['']],['linkedLocationIds',['prison','prison']],['linkedLocationIds',['district']],['linkedLocationIds',['supply']]]){
    const data=snapshot(); data.locations[0][field]=value;
    assert.throws(()=>normalizeData(data),undefined,JSON.stringify([field,value]));
  }
  const cycle=snapshot();cycle.locations[1].isLocation=true;cycle.locations[1].linkedLocationIds=['district'];
  assert.throws(()=>normalizeData(cycle),/Цикл|циклическ/i);
  const notLocation=snapshot();notLocation.locations[0].isLocation=false;
  assert.throws(()=>normalizeData(notLocation),/Локаци|isLocation/i);
});

test('canonical links roundtrip literally without duplicating child effects or inheriting parent ownership',()=>{
  const data=frozen(snapshot());const normalized=normalizeData(data);
  assert.deepEqual(normalized,data);assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)),data);
  assert.equal(normalized.locations[1].faction,'prison-house');
  assert.deepEqual(normalized.locations[0].objects,[]);
  assert.deepEqual(normalized.locations[1].objects,data.locations[1].objects);
  const edited=updateLocation(data,'district',{description:'  Новый текст  '});
  assert.deepEqual(edited.locations[0].linkedLocationIds,['prison']);
  assert.deepEqual(edited.locations[1],data.locations[1]);
});

test('deleting a linked target removes only incoming references without deleting other markers or effects',()=>{
  const data=snapshot();data.locations[0].linkedLocationIds=['other','prison'];data.locations[2].isLocation=true;data.locations[2].linkedLocationIds=['prison'];
  const before=structuredClone(data),result=removeLocation(frozen(data),'prison');
  assert.deepEqual(result.locations.map(l=>l.id),['district','other']);
  assert.deepEqual(result.locations[0].linkedLocationIds,['other']);assert.deepEqual(result.locations[1].linkedLocationIds,[]);
  for(const field of ['meta','factions','territories','nobles','sources','custom']) assert.deepEqual(result[field],before[field],field);
  assert.deepEqual(data,before);
});

test('deleting a container never cascades into its canonical children',()=>{
  const data=frozen(snapshot()); const result=removeLocation(data,'district');
  assert.deepEqual(result.locations,data.locations.slice(1));
  assert.deepEqual(result.locations[0].objects,data.locations[1].objects);
});

test('legacy map snapshots remain unchanged and link edits preserve literal whitespace IDs',()=>{
  const data=snapshot();delete data.locations[0].isLocation;delete data.locations[0].linkedLocationIds;
  assert.deepEqual(normalizeData(data),data);
  const renamed=snapshot();renamed.locations[1].id='  prison  ';renamed.locations[0].linkedLocationIds=['  prison  '];
  assert.deepEqual(normalizeData(renamed),renamed);
  const bad=structuredClone(renamed);bad.locations[0].linkedLocationIds=['prison'];assert.throws(()=>normalizeData(bad));
  const noOp=updateLocation(data,'other',{});assert.deepEqual(noOp,data);
});
