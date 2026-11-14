import test from 'node:test';
import assert from 'node:assert/strict';
import { reconcileDraftPublication } from '../assets/js/draft-publication.mjs';
const prior=()=>({version:1,meta:{width:100,height:100},factions:[{id:'g',name:'Королевство',color:'#a74657',parent:null,ruler:''}],locations:[{id:'a',name:'Место',x:5,y:7,type:'estate',faction:'g',owner:'',description:'Старое описание',objects:[],provenance:{sources:[1]}},{id:'b',name:'Другое',x:6,y:8,type:'estate',faction:'g',owner:'',description:'Исходный текст',objects:[]}],nobles:[{id:'n',name:'Барон',description:'Старая биография',sources:[1]}],sources:[{id:1,title:'Вики',url:'https://wowpedia.fandom.com/wiki/Gilneas'}],territories:[]});
const published=()=>{const d=prior();d.meta.publicationRevision='faction-dossiers-v2';d.meta.gilneasCrest='assets/ui/gilneas-human.png';d.locations[0].description='Новый лоровый текст';d.locations[0].shortDescription='Краткий текст';d.locations[0].wowpediaUrl='https://wowpedia.fandom.com/wiki/Gilneas';d.locations[0].owner='Барон';d.nobles[0].appearance='Человек';d.nobles[0].description='Обновлённая биография';d.factions[0].ruler='Барон';return d;};

test('publication enriches an old full draft without replacing custom buildings, moved points or author text',()=>{
  const previous=prior(),release=published(),draft=prior();draft.locations[0].x=25;draft.locations[0].objects=[{id:'forge',name:'Кузница',type:'building',modifiers:[{id:'m',kind:'bonus',text:'Авторский бонус'}]}];draft.locations[1].description='Мой сценарный текст';draft.locations[1].owner='Автор';draft.locations.push({id:'custom',name:'Моё место',x:30,y:30,objects:[],description:'Не менять'});
  const before=structuredClone(draft),result=reconcileDraftPublication(draft,release,previous);
  assert.equal(result.locations[0].description,release.locations[0].description);assert.equal(result.locations[0].wowpediaUrl,release.locations[0].wowpediaUrl);assert.equal(result.locations[0].owner,'Барон');assert.equal(result.locations[0].x,25);assert.deepEqual(result.locations[0].objects,draft.locations[0].objects);assert.equal(result.locations[1].description,'Мой сценарный текст');assert.equal(result.locations[1].owner,'Автор');assert.deepEqual(result.locations[2],draft.locations[2]);assert.equal(result.nobles[0].appearance,'Человек');assert.equal(result.meta.gilneasCrest,release.meta.gilneasCrest);assert.deepEqual(draft,before);
});

test('deleted authored records stay deleted, modified owners remain and a second reconciliation is idempotent',()=>{
  const old=prior(),release=published(),draft=prior();draft.locations=draft.locations.filter(l=>l.id!=='b');draft.locations[0].owner='Мой владелец';draft.nobles[0].description='Личная биография';draft.meta.customSetting='Моё значение';
  const once=reconcileDraftPublication(draft,release,old),twice=reconcileDraftPublication(once,release,old);assert.deepEqual(twice,once);assert.equal(once.locations.length,1);assert.equal(once.locations[0].owner,'Мой владелец');assert.equal(once.nobles[0].description,'Личная биография');assert.equal(once.meta.customSetting,'Моё значение');
});
