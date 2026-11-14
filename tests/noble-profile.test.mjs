import test from 'node:test';
import assert from 'node:assert/strict';
import { deriveNobleProfile } from '../assets/js/noble-profile.mjs';
const fixture=()=>({factions:[{id:'gilneas',name:'Королевство Гилнеас',parent:null,ruler:'Генн Седогрив',color:'#a74657'},{id:'greymane',name:'Дом Седогривов',parent:'gilneas',ruler:'Генн Седогрив',color:'#c49b60'},{id:'crowley',name:'Дом Краули',parent:'gilneas',ruler:'Дариус Краули',color:'#639096'},{id:'silverlaine',name:'Дом Сребролена',parent:'crowley',ruler:'Барон Сребролен',color:'#93a798'}],locations:[{id:'capital',name:'Город Гилнеас',faction:'greymane',owner:'Генн Седогрив',objects:[]},{id:'pyrewood',name:'Пирвуд',faction:'crowley',owner:'Дариус Краули',objects:[]},{id:'orchard',name:'Сад Краули',faction:'crowley',owner:'',objects:[]},{id:'keep',name:'Замок',faction:'silverlaine',owner:'Барон Сребролен',objects:[{id:'forge',name:'Кузница',owner:'Дариус Краули',type:'building',faction:'crowley'},{id:'guild',name:'Гильдия',owner:'Барон Сребролен',type:'building',faction:null}]}],nobles:[{id:'genn',name:'Генн Седогрив',house:'greymane',title:'Король',description:'Король страны',appearance:'Человек',sources:[1]},{id:'darius',name:'Дариус Краули',house:'crowley',title:'Лорд',description:'Советник',appearance:'Человек',sources:[2]},{id:'silver',name:'Барон Сребролен',house:'silverlaine',title:'Барон',description:'Лорд замка',appearance:'Человек',sources:[3]},{id:'guest',name:'Гость',house:null,role:'guest',title:'Претендент',description:'При дворе',sources:[]}],sources:[{id:1,title:'Генн',url:'https://wowpedia.fandom.com/wiki/Genn_Greymane'},{id:2,title:'Краули',url:'https://wowpedia.fandom.com/wiki/Darius_Crowley'},{id:3,title:'Сребролен',url:'https://wowpedia.fandom.com/wiki/Baron_Silverlaine'}]});

test('noble profile resolves actual suzerain and complete direct/house/vassal holdings without duplicate IDs',()=>{
  const data=fixture(),before=structuredClone(data),profile=deriveNobleProfile(data,'darius');
  assert.equal(profile.name,'Дариус Краули');
  assert.equal(profile.house.name,'Дом Краули');
  assert.equal(profile.suzerain.ruler,'Генн Седогрив');
  assert.equal(profile.suzerain.factionId,'gilneas');
  assert.equal(profile.isSovereign,false);
  assert.deepEqual(profile.holdings.map(h=>[h.kind,h.id,h.scope]),[['location','pyrewood','personal'],['location','orchard','house'],['location','keep','vassal'],['object','forge','personal']]);
  assert.equal(new Set(profile.holdings.map(h=>h.kind+':'+h.id)).size,profile.holdings.length);
  assert.deepEqual(data,before);
});

test('sovereign is not his own vassal and independent objects are not inherited into domain holdings',()=>{
  const data=fixture(),king=deriveNobleProfile(data,'genn'),baron=deriveNobleProfile(data,'silver');
  assert.equal(king.isSovereign,true);
  assert.equal(king.suzerain,null);
  assert.equal(baron.suzerain.factionId,'crowley');
  assert.equal(baron.suzerain.ruler,'Дариус Краули');
  assert.deepEqual(baron.holdings.map(h=>h.id),['keep','guild']);
});

test('unknown appearance and guest allegiance remain explicit without invented property or titles',()=>{
  const data=fixture(),guest=deriveNobleProfile(data,'guest');
  assert.equal(guest.house,null);assert.equal(guest.suzerain,null);assert.equal(guest.isSovereign,false);
  assert.deepEqual(guest.holdings,[]);
  assert.match(guest.appearance,/не описана|не установлена/i);
  assert.throws(()=>deriveNobleProfile(data,'not-known'),/не найден/i);
});
