import test from 'node:test';
import assert from 'node:assert/strict';

const old=()=>({version:1,meta:{width:100,height:120,image:'assets/maps/old.webp',mist:'old-mist.webp',inactiveMask:'old-mask.png',labels:[]},factions:[{id:'realm',name:'Держава',parent:null,color:'#8899aa'}],locations:[{id:'city',name:'Город',x:40,y:60,faction:'realm',owner:'',description:'Авторский текст',objects:[]},{id:'port',name:'Гавань',x:15,y:90,faction:'realm',objects:[]}],territories:[{id:'region',faction:'realm',points:[[20,20],[70,20],[70,100],[20,100]]}],nobles:[],sources:[]});
const release=()=>{const d=old();d.meta={...d.meta,width:120,height:110,image:'assets/maps/new.webp',mist:'new-mist.webp',inactiveMask:'new-mask.png',mapRevision:'origins-map-v3',homeBounds:{x:0,y:0,width:120,height:110},labels:[{text:'Земли',x:80,y:60}]};d.locations[0].x=72;d.locations[0].y=49;d.locations[1].x=28;d.locations[1].y=78;d.territories[0].points=[[30,10],[80,10],[80,90],[30,90]];return d;};
const H=[[1,0,10],[0,1,-10],[0,0,1]];

test('map replacement adopts all reviewed baseline points but preserves author data and relocates author-moved points',async()=>{
  const {reconcileMapPublication}=await import('../assets/js/map-publication.mjs');
  const previous=old(),published=release(),draft=old();
  draft.locations[0].objects.push({id:'forge',type:'building',name:'Моя кузница',description:'',owner:'',modifiers:[{id:'bonus',kind:'bonus',text:'+5'}]});
  draft.locations[1].x=20;draft.locations.push({id:'custom',name:'Мой ориентир',x:80,y:70,faction:null,objects:[]});
  const before=structuredClone(draft);
  const result=reconcileMapPublication(draft,published,previous,H);
  assert.deepEqual([result.locations[0].x,result.locations[0].y],[72,49]);
  assert.deepEqual([result.locations[1].x,result.locations[1].y],[30,80]);
  assert.deepEqual([result.locations[2].x,result.locations[2].y],[90,60]);
  assert.equal(result.locations[0].description,'Авторский текст');
  assert.deepEqual(result.locations[0].objects,draft.locations[0].objects);
  assert.equal(result.meta.image,published.meta.image);
  assert.equal(result.meta.width,120);assert.equal(result.meta.height,110);
  assert.deepEqual(result.territories,published.territories);
  assert.deepEqual(draft,before);
  assert.deepEqual(reconcileMapPublication(result,published,previous,H),result);
});

test('manual ownership grid keeps zeros and faction indices through an explicit map translation',async()=>{
  const {reconcileMapPublication}=await import('../assets/js/map-publication.mjs');
  const previous=old(),published=release(),draft=old();
  draft.territoryGrid={version:1,width:10,height:12,step:10,mapWidth:100,mapHeight:120,keys:['realm'],cells:new Array(120).fill(0),radius:40,authorNote:'Ручная граница'};
  draft.territoryGrid.cells[4*10+4]=1;
  const result=reconcileMapPublication(draft,published,previous,H);
  assert.equal(result.territoryGrid.width,12);assert.equal(result.territoryGrid.height,11);
  assert.equal(result.territoryGrid.cells[3*12+5],1);
  assert.equal(result.territoryGrid.cells[3*12+4],0);
  assert.equal(result.territoryGrid.cells[0],0);
  assert.equal(result.territoryGrid.authorNote,'Ручная граница');
  assert.deepEqual(result.territoryGrid.keys,['realm']);
  assert.equal(result.territoryGrid.mapWidth,120);assert.equal(result.territoryGrid.mapHeight,110);
});

test('cropped author locations fail without deleting or clamping the original snapshot',async()=>{
  const {reconcileMapPublication}=await import('../assets/js/map-publication.mjs');
  const draft=old();draft.locations.push({id:'cropped',name:'Авторская северная точка',x:5,y:1,faction:null,objects:[]});
  const before=structuredClone(draft);
  assert.throws(()=>reconcileMapPublication(draft,release(),old(),H),/вне карты|не переносится/i);
  assert.deepEqual(draft,before);
});

test('author deletions and manual polygon edits survive the map-version boundary',async()=>{
  const {reconcileMapPublication}=await import('../assets/js/map-publication.mjs');
  const draft=old();draft.locations.splice(1,1);draft.territories[0].points=[[22,22],[68,22],[68,95],[22,95]];
  const result=reconcileMapPublication(draft,release(),old(),H);
  assert.equal(result.locations.length,1);
  assert.deepEqual(result.territories[0].points,[[32,12],[78,12],[78,85],[32,85]]);
});
