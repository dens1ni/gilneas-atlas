import test from 'node:test';
import assert from 'node:assert/strict';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';
import {normalizeData} from '../assets/js/model.mjs';
const previous=()=>({version:1,meta:{width:100,height:100,publicationRevision:'origins-dossiers-v3',wallConstruction:{value:10,max:100}},factions:[{id:'greymane',name:'Дом',color:'#c49b60',parent:null}],locations:[{id:'town',name:'Место',x:20,y:30,faction:'greymane',owner:'',description:'Лор',objects:[]}],nobles:[{id:'person',name:'Лорд',house:'greymane'}],sources:[{id:1,title:'Источник',url:'https://example.invalid/one'}],territories:[]});
const published=()=>{const data=previous();data.meta.publicationRevision='royal-council-v4';data.factions[0].heraldry={symbol:'assets/ui/factions/greymane-device.svg',edge:'#65707b',device:'#9aa8b6'};return data;};

test('new faction devices are adopted only if absent or unchanged; custom heraldry stays literal',()=>{
  const before=previous(),release=published(),draft=previous();
  const migrated=normalizeData(reconcileDraftPublication(draft,release,before));
  assert.deepEqual(migrated.factions[0].heraldry,release.factions[0].heraldry);
  const custom={symbol:'https://example.invalid/author.svg',edge:'#112233',device:'#445566',note:'  Автор  '};
  draft.factions[0].heraldry=custom;
  assert.deepEqual(reconcileDraftPublication(draft,release,before).factions[0].heraldry,custom);
  assert.equal(draft.meta.publicationRevision,'origins-dossiers-v3');
});

test('absent council receives safe release members without resurrecting deleted people or evidence',()=>{
  const before=previous(),release=published(),draft=previous();
  release.royalCouncil={version:1,members:[
    {id:'seat-house',kind:'faction',refId:'greymane',party:'royalists',stance:'support',advisor:false,active:true,note:'Проверка',sources:[1]},
    {id:'seat-person',kind:'person',refId:'person',party:'neutral',stance:'unknown',advisor:false,active:false,note:'',sources:[1]},
  ]};
  draft.nobles=[];draft.sources=[];
  const migrated=normalizeData(reconcileDraftPublication(draft,release,before));
  assert.deepEqual(migrated.royalCouncil,{version:1,members:[{...release.royalCouncil.members[0],sources:[]}]});
  assert.deepEqual(migrated.nobles,[]);
  assert.deepEqual(migrated.sources,[]);
});

test('edited council assignments and wall-event history are never overwritten by publication',()=>{
  const before=previous(),release=published(),draft=previous();
  release.royalCouncil={version:1,members:[]};
  draft.royalCouncil={version:1,members:[{id:'author-seat',kind:'person',name:'  Свой лорд  ',party:'neutral',stance:'unknown',advisor:false,active:true,note:'<script>literal</script>'}]};
  draft.meta.wallConstruction={value:43,max:100,baseValue:40,events:[{id:'author-event',name:'Авторское событие',description:'  Не менять  ',delta:3,effects:[]}]};
  const frozen=structuredClone(draft),result=reconcileDraftPublication(draft,release,before);
  assert.deepEqual(result.royalCouncil,draft.royalCouncil);
  assert.deepEqual(result.meta.wallConstruction,draft.meta.wallConstruction);
  assert.deepEqual(draft,frozen);
  assert.deepEqual(reconcileDraftPublication(result,release,before),result);
});
