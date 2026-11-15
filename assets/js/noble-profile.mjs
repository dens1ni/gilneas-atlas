import { effectiveFaction, factionMembers, sovereignOf } from './model.mjs';

/** Derive the dossier from the current snapshot; no cached or invented holdings. */
export function deriveNobleProfile(data, id) {
  const noble=data.nobles.find(record=>record.id===id);
  if(!noble)throw new Error('Персонаж не найден');
  if(typeof noble.name!=='string'||!noble.name.trim().length)throw new Error(`Некорректное имя персонажа: ${noble.id}`);
  const factions=new Map(data.factions.map(faction=>[faction.id,faction]));
  const house=factions.get(noble.house)??null;
  const root=house?factions.get(sovereignOf(data.factions,house.id)):null;
  const isSovereign=Boolean(root&&root.ruler===noble.name);
  const controlsHouse=Boolean(house&&house.ruler===noble.name);
  const authority=isSovereign?root?.id:controlsHouse?house?.id:null;
  const domain=authority?new Set(factionMembers(data.factions,authority)):new Set();
  const parent=!isSovereign&&controlsHouse&&house?.parent?factions.get(house.parent):null;
  const suzerain=parent?{factionId:parent.id,name:parent.name,ruler:parent.ruler||'Имя сюзерена не установлено'}:null;
  const holdings=[];
  const scope=(owner,faction)=>{
    if(owner===noble.name)return 'personal';
    if(faction!=null&&domain.has(faction))return faction===authority||faction===house?.id?'house':'vassal';
    return null;
  };
  for(const location of data.locations){
    const locationScope=scope(location.owner,location.faction);
    if(locationScope)holdings.push({kind:'location',id:location.id,name:location.name,type:location.type,locationId:location.id,faction:location.faction,owner:location.owner||'',scope:locationScope});
    for(const object of location.objects||[]){
      const objectScope=scope(object.owner||location.owner,effectiveFaction(location,object));
      if(objectScope)holdings.push({kind:'object',id:object.id,name:object.name,type:object.type,locationId:location.id,locationName:location.name,faction:effectiveFaction(location,object),owner:object.owner||location.owner||'',scope:objectScope});
    }
  }
  const ids=[...new Set([...(noble.sources||[]),...(noble.provenance?.sources||[]),...(noble.fieldSources?.lifeStatus||[])])];
  const sources=ids.map(sourceId=>data.sources.find(source=>source.id===sourceId)).filter(Boolean);
  return {...noble,house,isSovereign,suzerain,holdings,sources,appearance:noble.appearance||'Внешность для выбранной эпохи не описана в источниках.',socialStatus:noble.socialStatus||noble.title||'Положение не установлено'};
}
