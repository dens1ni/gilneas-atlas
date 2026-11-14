import fs from 'node:fs/promises';
import path from 'node:path';
import { normalizeData } from '../assets/js/model.mjs';
import { fileURLToPath } from 'node:url';

// Integrate only the finished, evidence-verified research by canonical ID.
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const researchPath=process.argv[2];
if(!researchPath)throw new Error('Pass the verified research JSON path');
const [original,research]=await Promise.all([fs.readFile(path.join(root,'assets/data/atlas.json'),'utf8').then(JSON.parse),fs.readFile(researchPath,'utf8').then(JSON.parse)]);
for(const kind of ['locations','nobles']){
  if(research[kind].length!==original[kind].length||research[kind].some((row,i)=>row.id!==original[kind][i].id||row.name!==original[kind][i].name))throw new Error('Research changed canonical IDs/order/names: '+kind);
}
const merged=structuredClone(original);
const sourceIds=new Set(merged.sources.map(source=>source.id));
let nextSourceId=Math.max(...merged.sources.map(source=>typeof source.id==='number'?source.id:0))+1;
const plain=text=>text.replace(/\[([^\]]*)\]\((?:[^()\s]|\([^()]*\))*(?:\s+"[^"]*")?\)/g,'$1').replace(/[*_`]/g,'');
const sourceMap=[];
for(const kind of ['locations','nobles']){
  for(let i=0;i<merged[kind].length;i++){
    const row=research[kind][i],record=merged[kind][i];
    for(const field of ['description','shortDescription','wowpediaUrl'])record[field]=row[field];
    if(kind==='locations'){
      if(record.id==='shadowfang'){record.owner='Барон Сребролен';record.subtitle='Баронская крепость';}
      record.sources=[...new Set([...(record.sources||[]),...row.sources])];
    }else{
      for(const field of ['appearance','socialStatus','allegiance','overlord','overlordText','role','biographyFrame','displayInEarlyCourt','spouse','relations','fieldSources'])if(Object.hasOwn(row,field))record[field]=structuredClone(row[field]);
      record.title=row.title.replace(/ · историческая справка/g,'');
      record.sources=[...new Set([...record.sources,...row.sources])];
      for(const evidence of row.additionalEvidence||[]){
        let source=merged.sources.find(item=>item.url===evidence.url);
        if(!source){source={id:nextSourceId++,title:record.name+' · Wowpedia',url:evidence.url,canonicalUrl:evidence.url,quote:plain(evidence.quote)};merged.sources.push(source);sourceIds.add(source.id);}
        record.sources.push(source.id);record.wowpediaUrl=evidence.url;
        sourceMap.push({recordId:record.id,sourceId:source.id,ledgerId:evidence.ledgerId,url:evidence.url});
      }
      record.sources=[...new Set(record.sources)];
    }
    record.loreSources=structuredClone(row.sentenceSources);
  }
}
const silver=merged.factions.find(faction=>faction.id==='silverlaine');silver.ruler='Барон Сребролен';
const descriptions={greymane:'Правящая династия Гилнеаса, чей двор объединяет столицу и западную королевскую резиденцию.',crowley:'Северный дом Дариуса Краули; Пирвуд и Янтарная мельница входят в его земли.',silverlaine:'Баронский дом северных земель Гилнеаса. Его крепость над Пирвудом подчинена дому Краули.',godfrey:'Дом королевского советника Винсента Годфри и связанное с ним придворное окружение.',ashbury:'Дом Эшбери, из поколения в поколение связанный со службой короне Седогривов.',marley:'Дом королевского советника Марли, владеющего провинцией у северных рубежей.',walden:'Дом гилнеасской знати, связанный с восточными прибрежными землями.'};
for(const faction of merged.factions)if(descriptions[faction.id])faction.description=descriptions[faction.id];
merged.meta.wallConstruction={value:10,max:100};
merged.meta.publicationRevision='faction-dossiers-v2';
merged.meta.gilneasCrest='assets/ui/gilneas-shield.svg';
merged.meta.crestSource=research.crest.sourceFileUrl;
merged.meta.era='Человеческий Гилнеас после Второй войны · открытые северные владения';
merged.meta.chronicle=[
 {title:'Двор Гилнеаса',text:'Генн Седогрив правит королевством, опираясь на совет влиятельных лордов. Краули выступает за общую защиту людских земель, а Годфри и Эшбери предпочитают беречь силы страны.',sources:[32,45,49,50]},
 {title:'Северные владения',text:'Деревня Погребальных Костров и Янтарная мельница принадлежат Дариусу Краули. Лесные дороги связывают эти земли с полуостровом и гилнеасской столицей.',sources:[2,32,35]},
 {title:'Королевская граница',text:'На совете обсуждают новый каменный рубеж на севере. Годфри указывает на горные преграды; Генну предстоит решить, где пройдёт линия, затрагивающая земли Марли и Краули.',sources:[46,49,52]},
 {title:'Королевства у Лордамера',text:'У берегов большого озера стоит Даларан — наземный город магов Кирин-Тора. На острове Фенриса возвышается лордеронская крепость, а северный двор Теренаса остаётся средоточием Альянса.',sources:[36,37,38,39,41]}
];
const crestId=nextSourceId++;
merged.sources.push({id:crestId,title:'Старое знамя Гилнеаса · Warcraft II',url:research.crest.retrievedFileUrl,canonicalUrl:research.crest.sourceFileUrl,quote:plain(research.crest.evidence[0].quote),note:'Warcraft II: Tides of Darkness manual, pg. 43; Warcraft II: Battle.net Edition manual, pg. 41. Attribution retained from the file description.'});
merged.meta.crestSourceId=crestId;
const data=normalizeData(merged);
for(let i=0;i<data.locations.length;i++){
 const a=data.locations[i],b=original.locations[i];
 for(const key of ['id','name','x','y','type','faction'])if(a[key]!==b[key])throw new Error('Unexpected location change: '+a.id+' '+key);
 if(a.id!=='shadowfang'&&a.owner!==b.owner)throw new Error('Unexpected private ownership change: '+a.id);
 if(JSON.stringify(a.objects)!==JSON.stringify(b.objects))throw new Error('Objects changed: '+a.id);
}
await fs.writeFile(path.join(root,'assets/data/atlas.json'),JSON.stringify(data,null,2)+'\n');
await fs.writeFile(path.join(root,'docs/revision-source-map.json'),JSON.stringify({sourceMap,crestSourceId:crestId,oldSourceIdsPreserved:true,locations:data.locations.length,nobles:data.nobles.length,sources:data.sources.length},null,2)+'\n');
console.log(JSON.stringify({locations:data.locations.length,nobles:data.nobles.length,sources:data.sources.length,ownerOverride:'shadowfang',crestSourceId:crestId}));
