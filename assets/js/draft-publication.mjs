/** Keep each published draft on its actual three-way comparison baseline. */
export function previousPublicationFile(meta={}) {
  if(meta.publicationRevision==='royal-council-v5')return 'publication-v5.json';
  if(meta.publicationRevision==='royal-council-v4')return 'publication-v4.json';
  if(typeof meta.publicationRevision==='string'&&meta.publicationRevision.startsWith('origins-'))return 'publication-v3.json';
  if(typeof meta.publicationRevision==='string'&&meta.publicationRevision.startsWith('faction-dossiers'))return 'publication-v2.json';
  return 'publication-v1.json';
}

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
  const previousNobleIds=new Set((previous.nobles||[]).map(record=>record.id));
  const currentNobleIds=new Set((result.nobles||[]).map(record=>record.id));
  const factionIdsForNobles=new Set((result.factions||[]).map(record=>record.id));
  const adoptedNobleIds=new Set();
  for(const incoming of published.nobles||[]){
    if(previousNobleIds.has(incoming.id)||currentNobleIds.has(incoming.id))continue;
    if(incoming.house!=null&&!factionIdsForNobles.has(incoming.house))continue;
    const record=structuredClone(incoming);
    if(Object.hasOwn(record,'sources'))record.sources=record.sources.filter(id=>sources.has(id)&&sources.get(id).url===publishedSources.get(id)?.url);
    if(record.provenance&&Object.hasOwn(record.provenance,'sources'))record.provenance.sources=record.provenance.sources.filter(id=>sources.has(id)&&sources.get(id).url===publishedSources.get(id)?.url);
    if(record.fieldSources&&Object.hasOwn(record.fieldSources,'lifeStatus'))record.fieldSources.lifeStatus=record.fieldSources.lifeStatus.filter(id=>sources.has(id)&&sources.get(id).url===publishedSources.get(id)?.url);
    result.nobles??=[];result.nobles.push(record);currentNobleIds.add(record.id);adoptedNobleIds.add(record.id);
  }
  const locationIds=new Set((result.locations||[]).map(record=>record.id));
  const fields={
    locations:['description','shortDescription','wowpediaUrl','owner','isLocation','linkedLocationIds'],
    factions:['description','ruler','heraldry'],
    nobles:['description','appearance','socialStatus','overlord','allegiance','holdingsNote','wowpediaUrl','sources','lifeStatus'],
  };
  for(const [collection,names] of Object.entries(fields)){
    const next=new Map((published[collection]||[]).map(record=>[record.id,record]));
    const old=new Map((previous[collection]||[]).map(record=>[record.id,record]));
    for(const record of result[collection]||[]){
      const release=next.get(record.id),base=old.get(record.id);if(!release||!base)continue;
      if(collection==='nobles'&&same(draft.nobles.find(item=>item.id===record.id)?.lifeStatus,base.lifeStatus)){
        for(const field of ['lifeStatusNote','lifeStatusBasis']){
          if(Object.hasOwn(release,field)&&same(record[field],base[field]))record[field]=structuredClone(release[field]);
        }
        if(Object.hasOwn(release.fieldSources||{},'lifeStatus')&&same(record.fieldSources?.lifeStatus,base.fieldSources?.lifeStatus)){
          record.fieldSources??={};
          record.fieldSources.lifeStatus=release.fieldSources.lifeStatus.filter(id=>sources.has(id)&&sources.get(id).url===publishedSources.get(id)?.url);
        }
      }
      for(const field of names){
        if(Object.hasOwn(release,field)&&same(record[field],base[field])){
          if(field==='linkedLocationIds'&&record.isLocation!==true)continue;
          const value=field==='sources'?release[field].filter(id=>sources.has(id)&&((base.sources||[]).includes(id)||sources.get(id).url===publishedSources.get(id)?.url)):
            field==='linkedLocationIds'?release[field].filter(id=>locationIds.has(id)):release[field];
          record[field]=structuredClone(value);
        }
      }
    }
  }
  result.meta??={};
  for(const field of ['gilneasCrest','crestSource','wallConstruction']){
    const oldBanner=field==='gilneasCrest'&&result.meta[field]==='assets/ui/gilneas-human-banner.png';
    if(Object.hasOwn(published.meta,field)&&(same(result.meta[field],previous.meta?.[field])||oldBanner))result.meta[field]=structuredClone(published.meta[field]);
  }
  // Absence after prior presence is an author deletion, not first adoption.
  if(Object.hasOwn(published,'royalCouncil')&&same(result.royalCouncil,previous.royalCouncil)){
    const council=structuredClone(published.royalCouncil);
    const factionIds=new Set((result.factions||[]).map(record=>record.id));
    const nobleIds=new Set((result.nobles||[]).map(record=>record.id));
    council.members=council.members.filter(member=>member.kind==='faction'?factionIds.has(member.refId):member.refId==null||
      nobleIds.has(member.refId)&&(previousNobleIds.has(member.refId)||adoptedNobleIds.has(member.refId)));
    for(const member of council.members){
      if(Object.hasOwn(member,'sources'))member.sources=member.sources.filter(id=>sources.has(id)&&sources.get(id).url===publishedSources.get(id)?.url);
    }
    result.royalCouncil=council;
  }else if(result.royalCouncil&&previous.royalCouncil&&published.royalCouncil){
    const council=result.royalCouncil,release=published.royalCouncil,base=previous.royalCouncil;
    if(Object.hasOwn(release,'influence')&&same(council.influence,base.influence))council.influence=structuredClone(release.influence);
    const oldMembers=new Map(base.members.map(member=>[member.id,member]));
    const newMembers=new Map(release.members.map(member=>[member.id,member]));
    for(const member of council.members){
      const old=oldMembers.get(member.id),incoming=newMembers.get(member.id);
      if(!old||!incoming||member.kind!=='person'||member.kind!==old.kind||member.kind!==incoming.kind||
        member.refId!==old.refId||member.refId!==incoming.refId||member.party!==old.party||member.party!==incoming.party)continue;
      if(Object.hasOwn(incoming,'influence')&&same(member.influence,old.influence))member.influence=structuredClone(incoming.influence);
    }
    const currentIds=new Set(council.members.map(member=>member.id));
    const currentRefs=new Set(council.members.filter(member=>member.kind==='person').map(member=>member.refId));
    const oldIds=new Set(base.members.map(member=>member.id));
    const factionIds=new Set((result.factions||[]).map(record=>record.id));
    const nobleIds=new Set((result.nobles||[]).map(record=>record.id));
    for(const incoming of release.members){
      if(oldIds.has(incoming.id)||currentIds.has(incoming.id)||
        incoming.kind==='person'&&currentRefs.has(incoming.refId))continue;
      if(incoming.kind==='faction'?!factionIds.has(incoming.refId):incoming.refId!=null&&
        (!nobleIds.has(incoming.refId)||!previousNobleIds.has(incoming.refId)&&!adoptedNobleIds.has(incoming.refId)))continue;
      const member=structuredClone(incoming);
      if(Object.hasOwn(member,'sources'))member.sources=member.sources.filter(id=>sources.has(id)&&sources.get(id).url===publishedSources.get(id)?.url);
      council.members.push(member);currentIds.add(member.id);
      if(member.kind==='person')currentRefs.add(member.refId);
    }
  }
  result.meta.publicationRevision=revision;
  return result;
}
