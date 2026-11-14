import { normalizeData, loadDraft, saveDraft, resetDraft, deserializeSnapshot, serializeSnapshot, removeObject } from './model.mjs';
import { initUI } from './ui.mjs';
import { initEditor } from './editor.mjs';
import { initChronicle } from './chronicle.mjs';
import { decorateIcons } from './icons.mjs';
import { exportSite, downloadFile } from './export.mjs';

const $=id=>document.getElementById(id);
const root=new URL('../../',import.meta.url);
let data,baseline,selectedId=null,ui,editor,chronicle,maskCanvas;
let isDraft=false,toastTimer;
function toast(message) {
  $('toast').textContent=String(message);$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,5500);
}
function updateDraftBadge() {
  $('draft-status').textContent=isDraft?'Локальный черновик':'Королевский архив';
}
function select(id) {
  if(!data.locations.some(l=>l.id===id))return;
  selectedId=id;ui.render();ui.setPanel('dossier',true);ui.focusLocation(id);editor?.refresh?.();
}
function commit(incoming) {
  const next=normalizeData(incoming);
  saveDraft(localStorage,next);
  data=next;isDraft=true;
  if(selectedId&&!data.locations.some(l=>l.id===selectedId))selectedId=null;
  ui.render();editor?.refresh?.();updateDraftBadge();
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
function canPlace(point) {
  const [x,y]=point;
  if(x<0||y<0||x>data.meta.width||y>data.meta.height)return false;
  if(!maskCanvas)return true;
  const px=Math.min(maskCanvas.width-1,Math.floor(x*maskCanvas.width/data.meta.width));
  const py=Math.min(maskCanvas.height-1,Math.floor(y*maskCanvas.height/data.meta.height));
  return maskCanvas.getContext('2d',{willReadFrequently:true}).getImageData(px,py,1,1).data[0]<128;
}
async function loadInactiveMask() {
  try {
    const image=new Image();image.src=new URL(data.meta.inactiveMask||'assets/maps/inactive-mask.png',root).href;await image.decode();
    maskCanvas=document.createElement('canvas');maskCanvas.width=image.naturalWidth;maskCanvas.height=image.naturalHeight;
    maskCanvas.getContext('2d',{willReadFrequently:true}).drawImage(image,0,0);
  }catch(error){console.warn('Маска неактивных земель недоступна',error);toast('Не удалось загрузить маску неактивных земель.');}
}
async function deleteObject(locationId,objectId) {
  if(await confirmAction('Удалить объект?','Объект и его модификаторы будут удалены из локального черновика.')) {
    try{commit(removeObject(data,locationId,objectId));toast('Объект удалён.');}catch(error){toast(error.message);}
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
  if(file.size>20000000)throw Error('Файл снимка слишком велик');
  const next=deserializeSnapshot(await file.text());commit(next);toast('Атлас восстановлен из JSON.');return next;
}
async function onReset() {
  if(!(await confirmAction('Восстановить королевский архив?','Все локальные изменения будут отменены. Опубликованный сайт и скачанные резервные копии не изменятся.')))return;
  resetDraft(localStorage);data=normalizeData(baseline);isDraft=false;selectedId=null;ui.render();editor?.refresh?.();updateDraftBadge();toast('Опубликованный атлас восстановлен.');
}
function wireDialogs() {
  document.querySelectorAll('[data-close]').forEach(button=>button.onclick=()=>$(button.dataset.close).close());
  document.querySelectorAll('dialog').forEach(dialog=>{
    let outsideDown=false;
    const outside=e=>{const r=dialog.getBoundingClientRect();return e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom;};
    dialog.addEventListener('pointerdown',e=>outsideDown=e.target===dialog&&outside(e));
    dialog.addEventListener('click',e=>{if(dialog.id!=='confirmation'&&e.target===dialog&&outsideDown&&outside(e))dialog.close();outsideDown=false;});
  });
  $('help-open').onclick=()=>openDialog('help');
  $('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{toast('Полный экран недоступен в этом браузере.');}};
  document.addEventListener('keydown',e=>{
    if(e.target.closest('input,textarea,select,[contenteditable=true]')||document.querySelector('dialog[open]'))return;
    if(e.key.toLowerCase()==='e'||e.key.toLowerCase()==='у') {if(selectedId){e.preventDefault();editor.editLocation(selectedId);}}
  });
}
async function start() {
  decorateIcons();wireDialogs();
  const response=await fetch(new URL('assets/data/atlas.json',root),{cache:'no-store'});
  if(!response.ok)throw Error('Королевский реестр недоступен: '+response.status);
  baseline=normalizeData(await response.json());
  let restored;
  try{restored=loadDraft(localStorage,baseline);}catch(error){restored={data:baseline,isDraft:false,error};}
  data=restored.data;isDraft=restored.isDraft;
  chronicle=initChronicle(()=>data);
  ui=initUI({getData:()=>data,getSelectedId:()=>selectedId,onSelect:select,
    onEditLocation:id=>editor.editLocation(id),onAddObject:id=>editor.addObject(id),
    onEditObject:(lid,oid)=>editor.editObject(lid,oid),onDeleteObject:deleteObject,
    onShowNoble:id=>chronicle.open('nobles',id)});
  editor=initEditor({getData:()=>data,getSelectedId:()=>selectedId,replaceData:commit,
    onSelect:select,ui,toast,confirm:confirmAction,onExportSite,onExportJson,onImport,onReset,canPlace});
  $('editor-open').onclick=()=>editor.open();
  updateDraftBadge();await loadInactiveMask();
  window.gilneasApp={ready:true,getData:()=>normalizeData(data),getSelectedId:()=>selectedId,
    selectId:select,replaceData:commit,ui,editor,chronicle,canPlace,exportSite:onExportSite,
    exportJson:onExportJson,importSnapshot:onImport,resetDraft:onReset};
  if(restored.error)toast('Черновик не прочитан. Открыт опубликованный атлас; повреждённый снимок сохранён в браузере.');
}
start().catch(error=>{
  console.error(error);toast('Атлас не загрузился: '+error.message);
  $('location-list').textContent='Не удалось открыть атлас. Проверьте наличие папки assets и подключение к сайту.';
});
