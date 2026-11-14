import test from 'node:test';
import assert from 'node:assert/strict';
import { deriveNobleProfile } from '../assets/js/noble-profile.mjs';

const fixture=()=>({factions:[{id:'kingdom',name:'Держава',ruler:'Король',parent:null},{id:'house',name:'Дом',ruler:'Нынешний лорд',parent:'kingdom'}],locations:[{id:'estate',name:'Домовые земли',faction:'house',owner:'',objects:[]}],nobles:[{id:'lord',name:'Нынешний лорд',house:'house',sources:[]},{id:'historical',name:'Историческая персона',house:'house',role:'historical_reference',overlordText:'Ранняя служба не установлена',sources:[]}],sources:[]});

test('membership in a house does not make a historical person its ruler or assign a living suzerain',()=>{
 const historical=deriveNobleProfile(fixture(),'historical');
 assert.deepEqual(historical.holdings,[]);
 assert.equal(historical.suzerain,null);
 assert.equal(historical.overlordText,'Ранняя служба не установлена');
 const lord=deriveNobleProfile(fixture(),'lord');
 assert.equal(lord.holdings.length,1);assert.equal(lord.suzerain.ruler,'Король');
});
