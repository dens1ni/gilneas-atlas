import test from 'node:test';
import assert from 'node:assert/strict';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';
import {normalizeData} from '../assets/js/model.mjs';

const previous=()=>({version:1,meta:{width:100,height:100,publicationRevision:'royal-council-v4'},locations:[],territories:[],
  factions:[{id:'royal-house',name:'Тестовый дом',parent:null,color:'#778899'}],sources:[{id:1,title:'Тестовый архив',url:'https://example.invalid/one'}],
  nobles:[{id:'test-king',name:'Тестовый король',house:'royal-house',description:'Первичный текст',sources:[1]},{id:'old-person',name:'Старая запись'}],
  royalCouncil:{version:1,members:[{id:'seat-king',kind:'person',refId:'test-king',party:'royalists',stance:'unknown',active:true,advisor:false,note:'Первая заметка',sources:[1]}]}});
const publication=()=>{const value=previous();value.meta.publicationRevision='royal-council-v5';
  value.sources.push({id:'family-source-test',title:'Тестовая родословная',url:'https://example.invalid/family'});
  value.nobles[0].lifeStatus='alive';
  value.nobles.push({id:'new-queen',name:'Тестовая королева',house:'royal-house',description:'  Источник королевы  ',lifeStatus:'alive',sources:['family-source-test']});
  value.royalCouncil.members.push({id:'seat-queen',kind:'person',refId:'new-queen',party:'neutral',stance:'unknown',active:true,advisor:false,note:'  Голос неизвестен  ',sources:['family-source-test'],influence:{party:0,kingdom:40}});
  return value;};

test('new verified family people and Council records enrich a custom draft without restoring author deletions',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  draft.nobles=draft.nobles.filter(noble=>noble.id!=='old-person');
  draft.nobles[0].description='  Авторский король  ';
  draft.royalCouncil.members[0].note='  Авторский протокол  ';draft.royalCouncil.extension={literal:[0,'0']};
  const untouched=structuredClone(draft),result=normalizeData(reconcileDraftPublication(draft,release,before));
  assert.deepEqual(result.nobles.map(noble=>noble.id),['test-king','new-queen']);
  assert.equal(result.nobles[0].description,draft.nobles[0].description);
  assert.equal(result.nobles[0].lifeStatus,'alive');
  assert.deepEqual(result.nobles[1],release.nobles[2]);
  assert.deepEqual(result.royalCouncil.members[0],draft.royalCouncil.members[0]);
  assert.deepEqual(result.royalCouncil.members[1],release.royalCouncil.members[1]);
  assert.deepEqual(result.royalCouncil.extension,draft.royalCouncil.extension);
  assert.deepEqual(draft,untouched);
  assert.deepEqual(reconcileDraftPublication(result,release,before),result);
});

test('author statuses and author people with a colliding exact ID or Council ref remain literal',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  draft.nobles[0].lifeStatus='unknown';
  const authorPerson={id:'new-queen',name:'  Другая персона автора  ',lifeStatus:'dead',custom:{keep:true}};
  draft.nobles.push(authorPerson);
  const authorSeat={id:'author-seat',kind:'person',refId:'new-queen',party:'internationalists',stance:'oppose',active:true,advisor:false,note:'  Авторский голос  ',influence:{party:17,kingdom:0}};
  draft.royalCouncil.members.push(authorSeat);
  const result=reconcileDraftPublication(draft,release,before);
  assert.equal(result.nobles[0].lifeStatus,'unknown');
  assert.deepEqual(result.nobles.at(-1),authorPerson);
  assert.deepEqual(result.royalCouncil.members.at(-1),authorSeat);
  assert.equal(result.royalCouncil.members.filter(member=>member.refId==='new-queen').length,1);
});

test('an author-created person with a release ID never receives a fabricated canonical Council appointment',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  draft.royalCouncil.members[0].note='  Свой протокол  ';
  draft.nobles.push({id:'new-queen',name:'  Авторская совпавшая запись  ',lifeStatus:'unknown'});
  const result=reconcileDraftPublication(draft,release,before);
  assert.deepEqual(result.royalCouncil.members,draft.royalCouncil.members);
  assert.deepEqual(result.nobles.at(-1),draft.nobles.at(-1));
});

test('an unchanged Council also avoids assigning new lore to a colliding author person',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  draft.nobles.push({id:'new-queen',name:'  Чужая совпавшая запись  ',lifeStatus:'unknown'});
  const result=reconcileDraftPublication(draft,release,before);
  assert.deepEqual(result.royalCouncil.members,draft.royalCouncil.members);
});

test('deleted previous Council assignments remain deleted while only brand new family seats are added',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  draft.royalCouncil.members=[];
  const result=reconcileDraftPublication(draft,release,before);
  assert.deepEqual(result.royalCouncil.members,[release.royalCouncil.members[1]]);
  assert.equal(result.royalCouncil.members.some(member=>member.id==='seat-king'),false);
});

test('absent source status and a custom field remain unchanged if no new status is published',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  delete release.nobles[0].lifeStatus;
  draft.nobles[0].custom={literal:'  Автор  '};
  const result=reconcileDraftPublication(draft,release,before);
  assert.equal(Object.hasOwn(result.nobles[0],'lifeStatus'),false);
  assert.deepEqual(result.nobles[0].custom,draft.nobles[0].custom);
});

test('historical status evidence enriches unchanged fields without replacing author metadata or custom statuses',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  before.nobles[0].fieldSources={description:[1]};draft.nobles[0].fieldSources={description:[1],custom:[1]};
  release.nobles[0].lifeStatusNote='  Установлено до начала войны  ';release.nobles[0].lifeStatusBasis='lore';
  release.nobles[0].fieldSources={description:[1],lifeStatus:['family-source-test']};
  const result=reconcileDraftPublication(draft,release,before);
  assert.equal(result.nobles[0].lifeStatusNote,release.nobles[0].lifeStatusNote);
  assert.equal(result.nobles[0].lifeStatusBasis,'lore');
  assert.deepEqual(result.nobles[0].fieldSources,{description:[1],custom:[1],lifeStatus:['family-source-test']});
  draft.nobles[0].lifeStatus='dead';draft.nobles[0].lifeStatusNote='  Сценарная смерть автора  ';
  assert.deepEqual(reconcileDraftPublication(draft,release,before).nobles[0],draft.nobles[0]);
});

test('new person status evidence never retains a removed or retargeted canonical source ID',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  release.nobles.at(-1).fieldSources={lifeStatus:[1,'family-source-test'],appearance:[1],custom:{literal:'  Не менять  '}};
  draft.sources=[];
  const result=normalizeData(reconcileDraftPublication(draft,release,before));
  assert.deepEqual(result.nobles.at(-1).fieldSources,{lifeStatus:['family-source-test'],appearance:[1],custom:{literal:'  Не менять  '}});
});

test('a family addition never reuses an author-deleted or retargeted source as evidence',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  release.nobles.at(-1).sources=[1,'family-source-test'];
  release.nobles.at(-1).provenance={sources:[1,'family-source-test'],note:'  Дополнительные сведения  '};
  draft.sources=[];
  const result=normalizeData(reconcileDraftPublication(draft,release,before));
  assert.deepEqual(result.nobles.at(-1).sources,['family-source-test']);
  assert.deepEqual(result.nobles.at(-1).provenance,{sources:['family-source-test'],note:'  Дополнительные сведения  '});
});
