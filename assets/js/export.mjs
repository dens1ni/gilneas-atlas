const encoder = new TextEncoder();
const crcTable = new Uint32Array(256);
for (let n=0;n<256;n++) {
  let c=n;
  for(let k=0;k<8;k++) c=(c&1)?0xedb88320^(c>>>1):c>>>1;
  crcTable[n]=c>>>0;
}
export function crc32(bytes) {
  let c=0xffffffff;
  for(const b of bytes)c=crcTable[(c^b)&255]^(c>>>8);
  return (c^0xffffffff)>>>0;
}
function put(buffer,offset,value,size) {
  const view = new DataView(buffer.buffer,buffer.byteOffset,buffer.byteLength);
  if(size===2)view.setUint16(offset,value,true);else view.setUint32(offset,value,true);
}
function concat(parts) {
  const result = new Uint8Array(parts.reduce((n,p)=>n+p.length,0));
  let offset=0;
  for(const p of parts){result.set(p,offset);offset+=p.length;}
  return result;
}
export function createZip(entries) {
  if(!Array.isArray(entries)||entries.length>65535)throw Error('Слишком много ZIP-записей');
  const localParts=[],centralParts=[],seen=new Set();
  let offset=0,centralSize=0;
  for(const entry of entries) {
    const name=entry.name;
    if(typeof name!=='string'||!name||name.startsWith('/')||name.includes('\\')||name.split('/').some(p=>p==='..'||p==='.')||seen.has(name))throw Error('Неверный путь ZIP: '+name);
    seen.add(name);
    const nameBytes=encoder.encode(name),bytes=typeof entry.data==='string'?encoder.encode(entry.data):entry.data;
    if(!(bytes instanceof Uint8Array))throw Error('ZIP-данные должны быть байтами');
    if(nameBytes.length>65535||bytes.length>0xffffffff)throw Error('ZIP-запись слишком велика');
    const crc=crc32(bytes),local=new Uint8Array(30+nameBytes.length);
    put(local,0,0x04034b50,4);put(local,4,20,2);put(local,6,0x0800,2);
    put(local,8,0,2);put(local,14,crc,4);put(local,18,bytes.length,4);put(local,22,bytes.length,4);put(local,26,nameBytes.length,2);
    local.set(nameBytes,30);
    const central=new Uint8Array(46+nameBytes.length);
    put(central,0,0x02014b50,4);put(central,4,20,2);put(central,6,20,2);put(central,8,0x0800,2);put(central,10,0,2);put(central,16,crc,4);put(central,20,bytes.length,4);put(central,24,bytes.length,4);put(central,28,nameBytes.length,2);put(central,42,offset,4);central.set(nameBytes,46);
    localParts.push(local,bytes);centralParts.push(central);offset+=local.length+bytes.length;centralSize+=central.length;
  }
  const end=new Uint8Array(22);
  put(end,0,0x06054b50,4);put(end,8,entries.length,2);put(end,10,entries.length,2);put(end,12,centralSize,4);put(end,16,offset,4);
  return concat([...localParts,...centralParts,end]);
}
export function downloadFile(name,data,type='application/octet-stream') {
  const blob=data instanceof Blob?data:new Blob([data],{type});
  const url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download=name;link.style.display='none';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
}
export async function exportSite(snapshot) {
  const root = new URL('../../',import.meta.url);
  const manifestResponse=await fetch(new URL('assets/runtime-manifest.json',root));
  if(!manifestResponse.ok)throw Error('Список файлов экспорта недоступен');
  const files=await manifestResponse.json();
  const entries=await Promise.all(files.map(async name=> {
    if(name==='assets/data/atlas.json')return {name,data:encoder.encode(JSON.stringify(snapshot,null,2)+'\n')};
    // Pages' artifact action excludes dotfiles; restore them from public data.
    if(name==='.nojekyll')return {name,data:new Uint8Array(0)};
    const source=name==='.github/workflows/deploy-pages.yml'?'assets/export/deploy-pages.yml':name;
    const response=await fetch(new URL(source,root));
    if(!response.ok)throw Error('Файл экспорта недоступен: '+name+' ('+response.status+')');
    return {name,data:new Uint8Array(await response.arrayBuffer())};
  }));
  const zip=createZip(entries);
  downloadFile('Гилнеас-GitHub-Pages.zip',zip,'application/zip');
  return zip;
}
