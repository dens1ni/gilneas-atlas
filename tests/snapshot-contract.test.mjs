import test from 'node:test';
import assert from 'node:assert/strict';

// Newly-created worlds, houses and buildings must survive one exported snapshot.
test('HTML-facing archive data never changes literal player text or inherited ownership',async()=>{
  const {normalizeData,serializeSnapshot,deserializeSnapshot,upsertFaction,upsertObject}=await import('../assets/js/model.mjs');
  const base=normalizeData({version:1,meta:{width:3247,height:4860},factions:[{id:'gilneas',name:'Королевство Гилнеас',parent:null,color:'#973449'}],locations:[{id:'test-location',name:'Тестовая земля',x:123,y:456,faction:'gilneas',owner:'',objects:[]}],sources:[],nobles:[],territories:[]});
  const house=upsertFaction(base,{id:'test-house',name:'Дом «Алой розы»',parent:'gilneas',color:'#487f82'});
  const text='</script><script>window.__pwned=1</script>\n −2 к казне; +3 к урожаю';
  const withBuilding=upsertObject(house,'test-location',{id:'test-building',name:'  Кузница <img onerror="alert(1)">  ',type:'building',description:text,modifiers:[{id:'test-bonus',kind:'bonus',text:'Бонус: +3 снабжения'},{id:'test-penalty',kind:'penalty',text:'Штраф: −2 казны'}]});
  const actual=deserializeSnapshot(serializeSnapshot(withBuilding));
  assert.deepEqual(actual,withBuilding);
  assert.equal(actual.locations[0].objects[0].description,text);
  assert.equal(Object.hasOwn(actual.locations[0].objects[0],'faction'),false);
  assert.equal(actual.factions[1].parent,'gilneas');
});
