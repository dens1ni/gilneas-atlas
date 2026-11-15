import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeData,saveDraft} from '../assets/js/model.mjs';

const snapshot=()=>({version:1,meta:{width:100,height:100},factions:[{id:'house',name:'Дом',color:'#123456',parent:null}],locations:[],nobles:[{id:'lord',name:'Лорд',house:'house'}],sources:[],territories:[],royalCouncil:{version:1,members:[{id:'seat',kind:'person',refId:'lord',party:'royalists',stance:'unknown',advisor:false,active:true,note:'  Автор  '}],custom:{keep:true}}});

test('the full model rejects invalid party balances before changing storage',()=>{
  for(const balances of [{royalists:-1,internationalists:1},{royalists:1},{royalists:'5',internationalists:4},{royalists:1.5,internationalists:4},{royalists:Number.MAX_SAFE_INTEGER+1,internationalists:4},null]){
    const data=snapshot();data.royalCouncil.influence=balances;const calls=[];
    assert.throws(()=>saveDraft({setItem:(...args)=>calls.push(args)},data),undefined,JSON.stringify(balances));
    assert.deepEqual(calls,[]);
  }
});
