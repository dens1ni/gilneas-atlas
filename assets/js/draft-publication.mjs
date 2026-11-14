/** Three-way update: only unchanged published fields adopt new lore. */
export function reconcileDraftPublication(draft,published,previous){
  const revision=published.meta?.publicationRevision;
  if(!revision||draft.meta?.publicationRevision===revision){
    const result=structuredClone(draft);
    if(revision&&result.meta?.gilneasCrest==='assets/ui/gilneas-human-banner.png'&&Object.hasOwn(published.meta,'gilneasCrest'))result.meta.gilneasCrest=structuredClone(published.meta.gilneasCrest);
    return result;
  }
  const previousSourceIds=new Set((previous.sources||[]).map(source=>source.id));
  const draftSources=new Map((draft.sources||[]).map(source=>[source.id,source]));
  // New publication IDs may already belong to an author's unrelated evidence.
  for(const source of published.sources||[]){
    const author=draftSources.get(source.id);
    if(author&&!previousSourceIds.has(source.id)&&author.url!==source.url){
      throw new Error(`Source-ID conflict for ${JSON.stringify(source.id)}: draft URL ${JSON.stringify(author.url)} differs from published URL ${JSON.stringify(source.url)}. Export your draft, choose a free source ID and update its author references before retrying; no lore was merged.`);
    }
  }
  const result=structuredClone(draft);
  const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  const sources=new Map((result.sources||[]).map(source=>[source.id,source]));
  for(const source of published.sources||[])if(!sources.has(source.id)&&!previousSourceIds.has(source.id)){
    result.sources??=[];result.sources.push(structuredClone(source));sources.set(source.id,source);
  }
  const publishedSources=new Map((published.sources||[]).map(source=>[source.id,source]));
  const fields={
    locations:['description','shortDescription','wowpediaUrl','owner'],
    factions:['description','ruler'],
    nobles:['description','appearance','socialStatus','overlord','allegiance','holdingsNote','wowpediaUrl','sources'],
  };
  for(const [collection,names] of Object.entries(fields)){
    const next=new Map((published[collection]||[]).map(record=>[record.id,record]));
    const old=new Map((previous[collection]||[]).map(record=>[record.id,record]));
    for(const record of result[collection]||[]){
      const release=next.get(record.id),base=old.get(record.id);if(!release||!base)continue;
      for(const field of names){
        if(Object.hasOwn(release,field)&&same(record[field],base[field])){
          record[field]=structuredClone(field==='sources'?release[field].filter(id=>sources.has(id)&&((base.sources||[]).includes(id)||sources.get(id).url===publishedSources.get(id)?.url)):release[field]);
        }
      }
    }
  }
  result.meta??={};
  for(const field of ['gilneasCrest','crestSource','wallConstruction']){
    const oldBanner=field==='gilneasCrest'&&result.meta[field]==='assets/ui/gilneas-human-banner.png';
    if(Object.hasOwn(published.meta,field)&&(!Object.hasOwn(result.meta,field)||same(result.meta[field],previous.meta?.[field])||oldBanner))result.meta[field]=structuredClone(published.meta[field]);
  }
  result.meta.publicationRevision=revision;
  return result;
}
