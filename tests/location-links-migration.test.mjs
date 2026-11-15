import test from 'node:test';
import assert from 'node:assert/strict';
import {reconcileDraftPublication, previousPublicationFile} from '../assets/js/draft-publication.mjs';
import {normalizeData} from '../assets/js/model.mjs';

function previous(){return {version:1,meta:{width:100,height:100,publicationRevision:'origins-dossiers-v3'},factions:[{id:'realm',name:'Держава',color:'#123456',parent:null}],locations:[{id:'village',name:'Село',type:'settlement',x:10,y:10,faction:'realm',owner:'',description:'',objects:[]},{id:'mine',name:'Шахта',type:'mine',x:20,y:20,faction:'realm',owner:'',description:'',objects:[]}],nobles:[],sources:[],territories:[]};}
function publication(){const data=previous();data.meta.publicationRevision='royal-council-v5';Object.assign(data.locations[0],{isLocation:true,linkedLocationIds:['mine']});return data;}

test('unchanged old map records adopt reviewed location flags and canonical links without copying children',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  const result=normalizeData(reconcileDraftPublication(draft,release,before));
  assert.equal(result.locations[0].isLocation,true);
  assert.deepEqual(result.locations[0].linkedLocationIds,['mine']);
  assert.deepEqual(result.locations[0].objects,[]);
  assert.deepEqual(result.locations[1],draft.locations[1]);
  assert.deepEqual(draft,before);
  assert.deepEqual(reconcileDraftPublication(result,release,before),result);
});

test('migration filters new links to author-deleted targets instead of resurrecting them',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();draft.locations=draft.locations.filter(l=>l.id!=='mine');
  const result=normalizeData(reconcileDraftPublication(draft,release,before));
  assert.deepEqual(result.locations.map(l=>l.id),['village']);
  assert.equal(result.locations[0].isLocation,true);assert.deepEqual(result.locations[0].linkedLocationIds,[]);
  assert.deepEqual(draft.locations[0],before.locations[0]);
});

test('an author explicit non-location flag never receives publication-only links',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();draft.locations[0].isLocation=false;
  const result=normalizeData(reconcileDraftPublication(draft,release,before));
  assert.equal(result.locations[0].isLocation,false);
  assert.equal(Object.hasOwn(result.locations[0],'linkedLocationIds'),false,'Do not attach links to an author-disabled container');
  assert.deepEqual(draft.locations[0],{...before.locations[0],isLocation:false});
});

test('custom author links and explicit empty collections survive a release unchanged',()=>{
  const before=previous(),draft=structuredClone(before),release=publication();
  const own={id:'  author-target  ',name:'Своя метка',type:'farm',x:30,y:40,faction:null,owner:'',description:'  Автор  ',objects:[],extension:{literal:true}};
  draft.locations.push(own);Object.assign(draft.locations[0],{isLocation:true,linkedLocationIds:['  author-target  ']});
  let result=normalizeData(reconcileDraftPublication(draft,release,before));
  assert.deepEqual(result.locations[0].linkedLocationIds,['  author-target  ']);assert.deepEqual(result.locations[2],own);
  draft.locations[0].linkedLocationIds=[];result=normalizeData(reconcileDraftPublication(draft,release,before));assert.deepEqual(result.locations[0].linkedLocationIds,[]);
});

test('a royal-council-v4 draft resolves to its exact pre-link court baseline',()=>{
  assert.equal(previousPublicationFile({publicationRevision:'royal-council-v4'}),'publication-v4.json');
  assert.equal(previousPublicationFile({publicationRevision:'origins-dossiers-v3'}),'publication-v3.json');
});
