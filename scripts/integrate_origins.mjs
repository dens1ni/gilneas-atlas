import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {normalizeData,validatePolygon} from '../assets/js/model.mjs';
import {projectMapPoint} from '../assets/js/map-publication.mjs';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const coordinateFile=process.argv[2],registrationFile=process.argv[3];
if(!coordinateFile||!registrationFile)throw new Error('Pass reviewed coordinates and registration JSON paths');
const [before,review,registration]=await Promise.all([
  fs.readFile(path.join(root,'assets/data/publication-v2.json'),'utf8').then(JSON.parse),
  fs.readFile(coordinateFile,'utf8').then(JSON.parse),fs.readFile(registrationFile,'utf8').then(JSON.parse)]);
const coordinates=new Map(review.locations.map(record=>[record.id,record]));
if(review.width!==3526||review.height!==4548||review.locations.length!==39||coordinates.size!==39||before.locations.some(record=>!coordinates.has(record.id)))throw new Error('Expected every one of the 39 exact canonical IDs');
const data=structuredClone(before),H=registration.homography;
for(const location of data.locations){
  const point=coordinates.get(location.id);
  if(!Number.isFinite(point.x)||!Number.isFinite(point.y)||point.x<0||point.y<0||point.x>3526||point.y>4548)throw new Error('Invalid reviewed point: '+location.id);
  location.x=point.x;location.y=point.y;
}
for(const territory of data.territories){
  territory.points=territory.points.map(point=>projectMapPoint(point,H));
  // The northern capital is clipped by the new image, so use the visible edge.
  if(territory.id==='lordaeron-capital')territory.points=[[2825,0],[3435,0],[3435,260],[3210,390],[2950,300],[2775,90]];
  // Explicit scenario boundary follows the enlarged city, including its bridges.
  if(territory.id==='dalaran-lordamere')territory.points=[[2650,1300],[2760,1230],[2870,1130],[2950,1140],[3005,1210],[3110,1190],[3270,1090],[3410,1150],[3430,1330],[3370,1450],[3365,1570],[3250,1730],[3100,1795],[2940,1775],[2780,1690],[2680,1540]];
  if(territory.id==='greymane-west-land')territory.points=[[700,2950],[790,2890],[910,2960],[1030,3100],[970,3240],[820,3310],[670,3180]];
  if(territory.id==='crowley-south-land')territory.points=[[775,3500],[930,3490],[1025,3570],[1010,3650],[895,3720],[780,3660],[720,3560]];
  validatePolygon(territory.points);
}
data.territories.push(
  {id:'gilneas-western-coast',name:'Западные земли Гилнеаса',faction:'gilneas',points:[[640,2910],[850,2810],[1050,3030],[1240,3270],[1170,3500],[1050,3740],[790,3730],[590,3540],[560,3310]],provenance:{confidence:'reconstruction',sources:[2,32],note:'Сценарное влияние короны вокруг целой Темной Гавани и западных владений на новой авторской карте.'}},
  {id:'gilneas-headlands',name:'Западный каменистый мыс',faction:'gilneas',points:[[900,2470],[1040,2430],[1140,2550],[1100,2690],[965,2725],[880,2610]],provenance:{confidence:'reconstruction',sources:[2,32],note:'Сценарный контур западного мыса в пределах новой карты.'}},
  {id:'gilneas-galewatch-island',name:'Остров Штормового маяка',faction:'gilneas',points:[[1015,2110],[1120,2085],[1190,2200],[1170,2320],[1060,2325],[1005,2215]],provenance:{confidence:'reconstruction',sources:[2,32],note:'Сценарный контур острова; объект маяка размещён по видимой северной башне.'}},
  {id:'silverlaine-castle-lands',name:'Баронская крепость и окрестности',faction:'silverlaine',points:[[1555,1640],[1650,1595],[1780,1655],[1840,1775],[1750,1850],[1610,1815],[1535,1735]],provenance:{confidence:'reconstruction',sources:[32,35],note:'Сценарная земля младшего вассала дома Краули вокруг крепости барона Сребролена.'}}
);
for(const territory of data.territories)validatePolygon(territory.points);
Object.assign(data.meta,{width:3526,height:4548,image:'assets/maps/gilneas-origins-enhanced.webp',mist:'assets/maps/origins-inactive-mist.webp',inactiveMask:'assets/maps/origins-inactive-mask.png',enhancedWidth:5289,enhancedHeight:6822,mapRevision:'origins-map-v3',publicationRevision:'origins-dossiers-v3',mapRegistration:H,homeBounds:{x:450,y:2180,width:2480,height:2140},gilneasCrest:'assets/ui/gilneas-royal-shield.svg',gilneasHeraldry:{symbol:'assets/ui/gilneas-royal-symbol.png',field:'#131516',edge:'#65707b',device:'#9aa8b6',source:'user-supplied royal banner'}});
// Historical banner attribution remains in source 69, but the new UI image is
// explicitly supplied by the author, not attributed to that earlier file.
delete data.meta.crestSource;delete data.meta.crestSourceId;
data.factions.find(record=>record.id==='gilneas').color='#9aa8b6';
data.meta.labels=[{x:1970,y:2810,text:'Гилнеас',size:15},{x:2152,y:805,text:'Серебряный бор',size:12},{x:2990,y:820,text:'Лордамер',size:10}];
const validated=normalizeData(data);
for(const location of validated.locations){
  const old=before.locations.find(record=>record.id===location.id);
  for(const field of ['id','name','owner','faction','type','capital','description','shortDescription','wowpediaUrl','objects'])if(JSON.stringify(location[field])!==JSON.stringify(old[field]))throw new Error('Unrequested content change: '+location.id+' '+field);
}
await fs.writeFile(path.join(root,'assets/data/atlas.json'),JSON.stringify(validated,null,2)+'\n');
await fs.writeFile(path.join(root,'assets/data/origins-coordinates.json'),JSON.stringify(review,null,2)+'\n');
await fs.writeFile(path.join(root,'docs/origins-marker-verification.json'),JSON.stringify({locations:validated.locations.length,exactIdsPreserved:true,loreOwnersObjectsPreserved:true,originalDimensions:[3247,4860],newDimensions:[3526,4548],registration,reviewNotes:review.notes||[]},null,2)+'\n');
console.log(JSON.stringify({locations:validated.locations.length,nobles:validated.nobles.length,sources:validated.sources.length,mapRevision:validated.meta.mapRevision,customFeatures:['enlarged Dalaran','intact Duskhaven']}));
