import { deriveNobleProfile } from './noble-profile.mjs';
import { createFactionShield } from './heraldry.mjs';
import { createNobleLifeStatusTag } from './noble-life-status.mjs';

const colorOf=faction=>/^#[0-9a-f]{6}$/i.test(faction?.color||'')?faction.color:'#af9568';
const httpUrl=value=>{try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)?url.href:null;}catch{return null;}};
function element(tag,text='',className=''){
  const node=document.createElement(tag);node.textContent=text;if(className)node.className=className;return node;
}

export function initNobleDossier(ctx){
  const $=id=>document.getElementById(id),dialog=$('noble-dossier');
  let currentId=null;
  function close(){dialog.close();currentId=null;}
  function render(id=currentId){
    if(!id)return;
    const data=ctx.getData(),profile=deriveNobleProfile(data,id);
    dialog.style.setProperty('--noble-color',colorOf(profile.house));
    $('noble-name').textContent=profile.name;
    $('noble-title').textContent=profile.title||'';
    $('noble-title').append(createNobleLifeStatusTag(profile));
    $('noble-house').textContent=profile.house?.name||'Королевский архив';
    $('noble-house').style.color=colorOf(profile.house);
    $('noble-social-status').textContent=profile.socialStatus;
    $('noble-suzerain').textContent=profile.isSovereign?'Суверенный монарх — не является вассалом':profile.suzerain?`${profile.suzerain.ruler} · ${profile.suzerain.name}`:profile.overlordText||profile.allegiance||profile.overlord||'Вассальная связь не установлена';
    $('noble-description').textContent=profile.description||'Описание не внесено.';
    $('noble-appearance').textContent=profile.appearance;
    let crest=$('noble-crest');
    if(crest.tagName==='IMG'){
      const container=element('span','','noble-crest');container.id='noble-crest';
      crest.replaceWith(container);crest=container;
    }
    crest.setAttribute('aria-hidden','true');crest.hidden=false;
    crest.replaceChildren(createFactionShield(data,profile.house?.id??null));
    const holdings=$('noble-holdings');holdings.replaceChildren();
    const labels={personal:'Личное владение',house:'Земли дома',vassal:'Вассальные земли'};
    for(const holding of profile.holdings){
      const faction=data.factions.find(f=>f.id===holding.faction),button=element('button','','noble-holding');
      button.type='button';button.dataset.holdingId=holding.id;button.dataset.holdingKind=holding.kind;button.dataset.locationId=holding.locationId;
      button.style.setProperty('--holding-color',colorOf(faction));
      button.append(element('span',holding.name,'holding-name'),element('small',`${labels[holding.scope]}${holding.locationName?' · '+holding.locationName:''}${faction?' · '+faction.name:''}`));
      button.addEventListener('click',()=>{close();ctx.onSelect(holding.locationId);if(holding.kind==='object')requestAnimationFrame(()=>{
        const card=[...document.querySelectorAll('#dossier-objects [data-object-id]')].find(node=>node.dataset.objectId===holding.id);if(card)card.open=true;
      });});
      holdings.append(button);
    }
    if(!profile.holdings.length)holdings.append(element('p',profile.holdingsNote||'Владения этого персонажа не установлены по источникам.','noble-empty'));
    const sources=$('noble-sources');sources.replaceChildren();
    for(const source of profile.sources){
      const url=httpUrl(source.canonicalUrl)||httpUrl(source.url);if(!url)continue;
      const entry=element('div','','noble-source'),link=element('a',`[${source.id}] ${source.title||'Источник'}`);link.href=url;link.target='_blank';link.rel='noopener noreferrer';entry.append(link);
      if(source.quote)entry.append(element('blockquote',source.quote));sources.append(entry);
    }
  }
  function open(id){render(id);currentId=id;document.querySelectorAll('dialog[open]').forEach(node=>node.close());dialog.showModal();dialog.scrollTop=0;dialog.focus({preventScroll:true});}
  dialog.addEventListener('close',()=>{if(!dialog.open)currentId=null;});
  window.addEventListener('gilneas-data-changed',()=>{if(!dialog.open||!currentId)return;if(ctx.getData().nobles.some(n=>n.id===currentId))render();else close();});
  return {open,close,render};
}
