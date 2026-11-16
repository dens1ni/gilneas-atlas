import { normalizeData, loadDraft, saveDraft, resetDraft, deserializeSnapshot, serializeSnapshot, removeObject } from './model.mjs';
import { initUI } from './ui.mjs';
import { initEditor } from './editor.mjs';
import { initEditMode, isEditingEnabled } from './edit-mode.mjs';
import { reconcileDraftPublication, previousPublicationFile } from './draft-publication.mjs';
import { reconcileMapPublication } from './map-publication.mjs';
import { initTerritories, prepareTerritoryGrid, prepareRealmTerrain, requireRealmTerrain } from './territories.mjs';
import { initNobleDossier } from './noble-dossier.mjs';
import { initChronicle } from './chronicle.mjs';
import { initRoyalCouncilWindow } from './council-window.mjs';
import { initWallJournal } from './wall-journal.mjs';
import { initMapPresentation } from './map-presentation.mjs';
import { decorateIcons } from './icons.mjs';
import { exportSite, downloadFile } from './export.mjs';

const $=id=>document.getElementById(id);
const root=new URL('../../',import.meta.url);
let data,baseline,selectedId=null,ui,editor,chronicle,nobleDossier,boundaries,royalCouncil,wallJournal,mapPresentation;
const inactiveMasks=new Map();
let isDraft=false,toastTimer,editMode;
function toast(message) {
  $('toast').textContent=String(message);$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,5500);
}
function updateDraftBadge() {
  $('draft-status').textContent=isDraft?'Локальный черновик':'Королевский архив';
}
function select(id) {
  if(!data.locations.some(l=>l.id===id))return;
  selectedId=id;ui.render();ui.setPanel('dossier',true);ui.unfoldDossier?.();ui.focusLocation(id);editor?.refresh?.();
}
function clearSelection() {
  if(selectedId===null)return;
  selectedId=null;ui.setPanel('dossier',false);ui.render();editor?.refresh?.();
}
function requireEditing(revision) {
  if(!isEditingEnabled()||(revision!==undefined&&revision!==editMode.getRevision()))
    throw Error('Включите режим редактирования в Редакторе атласа.');
}
function commit(incoming) {
  requireEditing();
  const normalized=normalizeData(incoming);
  requireInactiveMask(normalized);
  requireRealmTerrain(normalized);
  mapPresentation.requirePrepared(normalized);
  const next=prepareTerritoryGrid(normalized,point=>canPlaceFor(normalized,point));
  saveDraft(localStorage,next);
  data=next;isDraft=true;
  if(selectedId&&!data.locations.some(l=>l.id===selectedId))selectedId=null;
  ui.render();mapPresentation.renderFrame(data);editor?.refresh?.();updateDraftBadge();
  window.dispatchEvent(new CustomEvent('gilneas-data-changed'));
  return data;
}
function openDialog(id) {
  document.querySelectorAll('dialog[open]').forEach(d=>d.close());$(id).showModal();$(id).focus();
}
function confirmAction(title,message) {
  return new Promise(resolve=>{
    $('confirm-title').textContent=title;$('confirm-message').textContent=message;
    const d=$('confirmation');
    const settle=value=>{d.close();$('confirm-yes').onclick=null;$('confirm-no').onclick=null;d.removeEventListener('cancel',cancel);resolve(value);};
    const cancel=e=>{e.preventDefault();settle(false);};
    $('confirm-yes').onclick=()=>settle(true);$('confirm-no').onclick=()=>settle(false);
    d.addEventListener('cancel',cancel);d.showModal();d.focus();
  });
}
function inactiveMaskKey(snapshot) {
  return new URL(snapshot.meta.inactiveMask||'assets/maps/inactive-mask.png',root).href;
}
function requireInactiveMask(snapshot) {
  const canvas=inactiveMasks.get(inactiveMaskKey(snapshot))?.canvas;
  if(!canvas)throw Error('Маска неактивных земель для этой карты ещё не загружена.');
  return canvas;
}
function canPlaceFor(snapshot,point) {
  const [x,y]=point;
  if(x<0||y<0||x>snapshot.meta.width||y>snapshot.meta.height)return false;
  const maskCanvas=requireInactiveMask(snapshot);
  const px=Math.min(maskCanvas.width-1,Math.floor(x*maskCanvas.width/snapshot.meta.width));
  const py=Math.min(maskCanvas.height-1,Math.floor(y*maskCanvas.height/snapshot.meta.height));
  return maskCanvas.getContext('2d',{willReadFrequently:true}).getImageData(px,py,1,1).data[0]<128;
}
function canPlace(point) {return canPlaceFor(data,point);}
async function loadInactiveMask(snapshot) {
  const key=inactiveMaskKey(snapshot);
  let entry=inactiveMasks.get(key);
  if(!entry){
    entry={canvas:null};inactiveMasks.set(key,entry);
    entry.ready=(async()=>{
      try{
        const image=new Image();
        await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=key;});
        const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;
        const context=canvas.getContext('2d',{willReadFrequently:true});context.drawImage(image,0,0);
        context.getImageData(0,0,1,1);
        entry.canvas=canvas;return canvas;
      }catch(error){inactiveMasks.delete(key);throw Error('Не удалось загрузить маску неактивных земель: '+key);}
    })();
  }
  return entry.ready;
}
async function deleteObject(locationId,objectId) {
  if(!isEditingEnabled())return;
  const revision=editMode.getRevision();
  if(await confirmAction('Удалить объект?','Объект и его модификаторы будут удалены из локального черновика.')) {
    try{requireEditing(revision);commit(removeObject(data,locationId,objectId));toast('Объект удалён.');}catch(error){toast(error.message);}
  }
}
async function onExportSite() {
  toast('Собираю карту и архив сайта…');
  try {await exportSite(normalizeData(data));toast('Архив для GitHub Pages сохранён.');}
  catch(error){toast('Экспорт не выполнен: '+error.message);throw error;}
}
function onExportJson() {
  downloadFile('Гилнеас-резервная-копия.json',serializeSnapshot(data),'application/json;charset=utf-8');toast('Полный снимок атласа сохранён.');
}
async function onImport(file) {
  if(!file)return;
  requireEditing();const revision=editMode.getRevision();
  if(file.size>20000000)throw Error('Файл снимка слишком велик');
  const next=deserializeSnapshot(await file.text());
  await Promise.all([loadInactiveMask(next),mapPresentation.prepare(next),next.territoryGrid ? prepareRealmTerrain(next) : Promise.resolve(null)]);
  requireEditing(revision);
  commit(next);toast('Атлас восстановлен из JSON.');return next;
}
async function onReset() {
  requireEditing();const revision=editMode.getRevision();
  if(!(await confirmAction('Восстановить королевский архив?','Все локальные изменения будут отменены. Опубликованный сайт и скачанные резервные копии не изменятся.')))return;
  await Promise.all([loadInactiveMask(baseline),mapPresentation.prepare(baseline),baseline.territoryGrid ? prepareRealmTerrain(baseline) : Promise.resolve(null)]);
  requireEditing(revision);
  const next=prepareTerritoryGrid(normalizeData(baseline),point=>canPlaceFor(baseline,point));
  resetDraft(localStorage);data=next;isDraft=false;selectedId=null;ui.render();mapPresentation.renderFrame(data);editor?.refresh?.();updateDraftBadge();
  window.dispatchEvent(new CustomEvent('gilneas-data-changed'));
  toast('Опубликованный атлас восстановлен.');
}
function wireDialogs() {
  document.querySelectorAll('[data-close]').forEach(button=>button.onclick=()=>$(button.dataset.close).close());
  document.querySelectorAll('dialog').forEach(dialog=>{
    if(dialog.dataset.backdropWired==='true')return;
    dialog.dataset.backdropWired='true';
    let outsideDown=false;
    const outside=e=>{const r=dialog.getBoundingClientRect();return e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom;};
    dialog.addEventListener('pointerdown',e=>outsideDown=e.target===dialog&&outside(e));
    dialog.addEventListener('click',e=>{if(dialog.id!=='confirmation'&&e.target===dialog&&outsideDown&&outside(e))dialog.close();outsideDown=false;});
  });
  $('help-open').onclick=()=>openDialog('help');
  $('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{toast('Полный экран недоступен в этом браузере.');}};
  document.addEventListener('keydown',e=>{
    if(e.target.closest('input,textarea,select,[contenteditable=true]')||document.querySelector('dialog[open]'))return;
    if(e.key.toLowerCase()==='e'||e.key.toLowerCase()==='у') {if(selectedId&&isEditingEnabled()){e.preventDefault();editor.editLocation(selectedId);}}
  });
}
async function start() {
  editMode=initEditMode({onChange:enabled=>{
    if(!enabled){
      editor?.cancelEditing?.();
      boundaries?.close();
      if($('confirmation').open)$('confirm-no').click();
    }
  }});
  mapPresentation=initMapPresentation();
  decorateIcons();wireDialogs();
  const response=await fetch(new URL('assets/data/atlas.json',root),{cache:'no-store'});
  if(!response.ok)throw Error('Королевский реестр недоступен: '+response.status);
  baseline=normalizeData(await response.json());
  let restored;
  try{restored=loadDraft(localStorage,baseline);}catch(error){restored={data:baseline,isDraft:false,error};}
  data=restored.data;isDraft=restored.isDraft;
  if(isDraft&&baseline.meta.publicationRevision&&data.meta.publicationRevision!==baseline.meta.publicationRevision){
    try{
      const previousVersion=previousPublicationFile(data.meta);
      const prior=await fetch(new URL('assets/data/'+previousVersion,root));
      if(!prior.ok)throw new Error('Предыдущая основа недоступна: '+prior.status);
      const previous=await prior.json();
      let authorSeed;
      if(['authored-estates-v6','authored-estates-v7','authored-estates-v8'].includes(baseline.meta.publicationRevision)){
        const seed=await fetch(new URL('assets/data/publication-author-v5.json',root),{cache:'no-store'});
        if(!seed.ok)throw new Error('Авторская основа недоступна: '+seed.status);
        authorSeed=await seed.json();
      }
      let next=reconcileDraftPublication(data,baseline,previous,authorSeed);
      if(baseline.meta.mapRevision&&next.meta.mapRevision!==baseline.meta.mapRevision){
        next=reconcileMapPublication(next,baseline,previous,baseline.meta.mapRegistration);
      }
      if(Object.hasOwn(baseline.meta,'gilneasHeraldry')&&!Object.hasOwn(data.meta,'gilneasHeraldry')&&!Object.hasOwn(previous.meta||{},'gilneasHeraldry')&&!Object.hasOwn(authorSeed?.meta||{},'gilneasHeraldry'))next.meta.gilneasHeraldry=structuredClone(baseline.meta.gilneasHeraldry);
      data=normalizeData(next);
    }catch(error){console.warn('Обновление не объединено с черновиком; сохранён ваш снимок.',error);toast('Сохранён ваш исходный черновик. Обновление не объединено: '+error.message);}
  }
  const [baselineMask]=await Promise.all([loadInactiveMask(baseline).catch(error=>{
    console.warn('Маска опубликованного атласа недоступна; восстановление потребует повторной загрузки.',error);return null;
  }),loadInactiveMask(data),mapPresentation.prepare(data)]);
  if(baselineMask)baseline=prepareTerritoryGrid(baseline,point=>canPlaceFor(baseline,point));
  data=prepareTerritoryGrid(data,canPlace);
  await Promise.all([prepareRealmTerrain(data),baseline.territoryGrid ? prepareRealmTerrain(baseline) : Promise.resolve(null)]);
  nobleDossier=initNobleDossier({getData:()=>data,onSelect:select});
  royalCouncil=initRoyalCouncilWindow({getData:()=>data,replaceData:commit,isEditingEnabled,toast,confirm:confirmAction,onShowNoble:id=>nobleDossier.open(id)});
  wallJournal=initWallJournal({getData:()=>data,replaceData:commit,isEditingEnabled,toast,confirm:confirmAction});
  chronicle=initChronicle(()=>data,{onOpenCouncil:()=>royalCouncil.open()});
  wireDialogs();
  ui=initUI({getData:()=>data,getSelectedId:()=>selectedId,onSelect:select,onClearSelection:clearSelection,
    onEditLocation:id=>editor.editLocation(id),onAddObject:id=>editor.addObject(id),
    onEditObject:(lid,oid)=>editor.editObject(lid,oid),onDeleteObject:deleteObject,
    onShowNoble:id=>nobleDossier.open(id),onRenderTerritories:state=>boundaries?.render({visible:state.visible,included:state.includedFactions?new Set(state.includedFactions):null})});
  editor=initEditor({getData:()=>data,getSelectedId:()=>selectedId,replaceData:commit,isEditingEnabled,
    onSelect:select,ui,toast,confirm:confirmAction,onExportSite,onExportJson,onImport,onReset,canPlace,onOpenTerritories:()=>boundaries.open()});
  boundaries=initTerritories({getData:()=>data,replaceData:commit,isEditingEnabled,ui,canPlace,toast});
  await boundaries.whenReady();
  mapPresentation.renderFrame(data);
  await mapPresentation.reveal();
  $('editor-open').onclick=()=>editor.open();
  updateDraftBadge();
  window.gilneasApp={ready:true,getData:()=>normalizeData(data),getSelectedId:()=>selectedId,
    selectId:select,clearSelection,replaceData:commit,ui,editor,chronicle,nobleDossier,boundaries,royalCouncil,wallJournal,mapPresentation,canPlace,exportSite:onExportSite,
    exportJson:onExportJson,importSnapshot:onImport,resetDraft:onReset};
  if(restored.error)toast('Черновик не прочитан. Открыт опубликованный атлас; повреждённый снимок сохранён в браузере.');
}
start().catch(error=>{
  mapPresentation?.fail(error);
  console.error(error);toast('Атлас не загрузился: '+error.message);
  $('location-list').textContent='Не удалось открыть атлас. Проверьте наличие папки assets и подключение к сайту.';
});
