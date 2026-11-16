/** Full-snapshot scenario migration; immutable publication is the first baseline. */
const own = (value, key) => value != null && Object.hasOwn(value, key);
const get = (value, key) => own(value, key) ? value[key] : undefined;
const set = (value, key, entry) => Object.defineProperty(value, key, {value: entry, enumerable: true, configurable: true, writable: true});
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const same = (a, b) => {
  if (Object.is(a, b)) return true;
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((value, i) => same(value, b[i]));
  if (!object(a) || !object(b)) return false;
  const keys = Object.keys(a);
  return keys.length === Object.keys(b).length && keys.every(key => own(b, key) && same(a[key], b[key]));
};
const index = records => new Map((records || []).map(record => [get(record, 'id'), record]));
const identity = (a, b) => !!a && !!b && ['name', 'type', 'x', 'y'].every(key => own(a, key) === own(b, key) && same(get(a, key), get(b, key)));
const keyed = value => Array.isArray(value) && value.every(record => object(record) && own(record, 'id'));

export function reconcileScenarioPublication(draft, published, previous, authorSeed) {
  const revision = published.meta?.publicationRevision;
  if (!revision || draft.meta?.publicationRevision === revision) return structuredClone(draft);
  const seed = authorSeed || {};
  const oldSources = index(previous.sources), draftSources = index(draft.sources), incomingSources = index(published.sources);
  for (const source of published.sources || []) {
    const current = draftSources.get(source.id);
    if (current && !oldSources.has(source.id) && current.url !== source.url) {
      throw new Error(`Source-ID conflict for ${JSON.stringify(source.id)}: draft URL ${JSON.stringify(current.url)} differs from published URL ${JSON.stringify(source.url)}. Export your draft and choose a free source ID before retrying; no scenario data was merged.`);
    }
  }
  const oldFactions = index(previous.factions), seedFactions = index(seed.factions);
  for (const faction of draft.factions || []) {
    if (!oldFactions.has(faction.id) && (published.factions || []).some(record => record.id === faction.id) && !same(faction, seedFactions.get(faction.id))) {
      throw new Error(`Faction-ID conflict for ${JSON.stringify(faction.id)}. Export your draft and rename the unrelated author faction ID and its references before retrying; no scenario data was merged.`);
    }
  }
  function modelIds(snapshot) {
    const records = new Map();
    const claim = (record, path) => { if (own(record, 'id')) records.set(get(record, 'id'), JSON.stringify(path)); };
    for (const collection of ['factions', 'locations', 'territories', 'nobles']) {
      for (const record of get(snapshot, collection) || []) {
        claim(record, [collection]);
        if (collection !== 'locations') continue;
        for (const entry of get(record, 'objects') || []) {
          claim(entry, ['locations', get(record, 'id'), 'objects']);
          for (const modifier of get(entry, 'modifiers') || []) claim(modifier, ['locations', get(record, 'id'), 'objects', get(entry, 'id'), 'modifiers']);
        }
      }
    }
    for (const route of get(get(get(snapshot, 'meta'), 'ferryNetwork'), 'routes') || []) {
      claim(route, ['meta', 'ferryNetwork', 'routes']);
    }
    // Route IDs are new, but every existing model collection can claim one.
    for (const source of get(snapshot, 'sources') || []) claim(source, ['sources']);
    for (const member of get(get(snapshot, 'royalCouncil'), 'members') || []) claim(member, ['royalCouncil', 'members']);
    for (const event of get(get(get(snapshot, 'meta'), 'wallConstruction'), 'events') || []) {
      claim(event, ['meta', 'wallConstruction', 'events']);
      for (const effect of get(event, 'effects') || []) claim(effect, ['meta', 'wallConstruction', 'events', get(event, 'id'), 'effects']);
    }
    return records;
  }
  const currentIds = modelIds(draft);
  for (const [id, path] of modelIds(published)) {
    if (currentIds.has(id) && currentIds.get(id) !== path) throw new Error(`ID conflict for ${JSON.stringify(id)}: draft ${currentIds.get(id)} conflicts with published ${path}. Export your draft and choose a free record ID before retrying; no scenario data was merged.`);
  }
  const result = structuredClone(draft);
  const oldLocations = index(previous.locations), seedLocations = index(seed.locations);
  const draftLocations = index(draft.locations);
  // Missing old pins make seed lineage ambiguous: absence is not adoption evidence.
  const intactOldLocations = oldLocations.size > 0 && [...oldLocations.keys()].every(id => draftLocations.has(id));
  const authorKnown = (draft.locations || []).some(record => {
    const authored = seedLocations.get(record.id), old = oldLocations.get(record.id);
    return identity(record, authored) && (!old || !identity(authored, old));
  }) || own(seed, 'territoryGrid') && own(draft, 'territoryGrid') && same(draft.territoryGrid, seed.territoryGrid) || !!authorSeed && !intactOldLocations;
  const sources = index(result.sources);
  const validSource = id => sources.has(id) && incomingSources.has(id) && sources.get(id).url === incomingSources.get(id).url;
  const eligible = {factions: new Set(), locations: new Set(), nobles: new Set()};
  for (const collection of Object.keys(eligible)) {
    const old = index(previous[collection]), authored = index(seed[collection]), current = index(draft[collection]);
    for (const release of published[collection] || []) {
      const record = current.get(release.id);
      if (old.has(release.id) ? !!record : record ? collection === 'locations' ? identity(record, authored.get(release.id)) : same(record, authored.get(release.id)) : !authorKnown || !authored.has(release.id)) eligible[collection].add(release.id);
    }
  }
  const validReference = (field, value) => value == null || (field === 'faction' || field === 'house' || field === 'parent' ? eligible.factions.has(value) : eligible.nobles.has(value));
  const referenceField = (path, field) => path === 'factions' && field === 'parent' || ['locations', 'locations.objects', 'territories'].includes(path) && field === 'faction' || path === 'nobles' && field === 'house' || ['nobles.relations', 'nobles.spouse'].includes(path) && field === 'nobleId';
  const allowedRecord = (record, path) => {
    if (path === 'royalCouncil.members') return record.kind === 'faction' ? eligible.factions.has(record.refId) : record.refId == null || eligible.nobles.has(record.refId);
    return Object.keys(record).every(field => !referenceField(path, field) || validReference(field, get(record, field)));
  };
  for (const collection of ['factions', 'nobles', 'locations']) {
    const current = index(draft[collection]);
    let changed;
    do {
      changed = false;
      for (const record of published[collection] || []) {
        if (!current.has(record.id) && eligible[collection].has(record.id) && !allowedRecord(record, collection)) {
          eligible[collection].delete(record.id); changed = true;
        }
      }
    } while (changed);
  }
  const sourcePaths = new Set([
    'locations.sources', 'locations.objects.sources', 'nobles.sources', 'territoryGrid.sources',
    ...['locations', 'locations.objects', 'factions', 'territories', 'nobles', 'territoryGrid'].map(path => `${path}.provenance.sources`),
    'nobles.spouse.sourceIds', 'nobles.relations.sourceIds', 'nobles.localization.sources',
    'royalCouncil.members.sources', 'meta.chronicle.sources',
    'meta.wallConstruction.events.sources', 'meta.wallConstruction.events.effects.sources',
    ...['allegiance', 'appearance', 'biographyFrame', 'description', 'englishName', 'house', 'lifeStatus', 'name', 'overlord', 'overlordText', 'relations', 'role', 'shortDescription', 'socialStatus', 'spouse', 'title'].map(field => `nobles.fieldSources.${field}`),
  ]);
  // A literal dotted extension key must not impersonate a schema path.
  const child = (path, key) => path ? `${path}.${key.includes('.') ? JSON.stringify(key) : key}` : key.includes('.') ? JSON.stringify(key) : key;
  function filter(value, path) {
    if (sourcePaths.has(path)) return value.filter(validSource);
    if (path === 'locations.linkedLocationIds') return value.filter(id => eligible.locations.has(id));
    if (['locations.loreSources', 'nobles.loreSources'].includes(path)) return value.map(ids => ids.filter(validSource));
    return value;
  }
  function clean(value, field = '', path = '') {
    if (path === 'meta.ferryNetwork') {
      const network = structuredClone(value);
      const ferry = id => eligible.locations.has(id) && (published.locations || []).some(record => record.id === id && record.type === 'ferry');
      network.routes = network.routes.filter(route => ferry(route.fromLocationId) && ferry(route.toLocationId));
      return network;
    }
    if (Array.isArray(value)) {
      if (sourcePaths.has(path) || ['locations.linkedLocationIds', 'locations.loreSources', 'nobles.loreSources'].includes(path)) return structuredClone(filter(value, path));
      return value.filter(record => !object(record) || allowedRecord(record, path)).map(record => clean(record, '', path));
    }
    if (!object(value)) return value;
    const copy = {};
    for (const [key, entry] of Object.entries(value)) {
      if (referenceField(path, key) && !validReference(key, entry)) continue;
      set(copy, key, clean(entry, key, child(path, key)));
    }
    return copy;
  }
  function unchanged(current, base, authored, key) {
    if (own(base, key) && !own(current, key)) return false;
    if (!own(base, key) && authorKnown && own(authored, key) && !own(current, key)) return false;
    return own(current, key) === own(base, key) && same(get(current, key), get(base, key)) || own(current, key) && own(authored, key) && same(get(current, key), get(authored, key)) && !same(get(authored, key), get(base, key));
  }
  function mergeArray(current, base, release, authored, path) {
    const old = index(base), seeds = index(authored), next = index(release), existing = index(current);
    for (const record of current) {
      const incoming = next.get(record.id), prior = old.get(record.id), author = seeds.get(record.id);
      if (!prior && author && path === 'locations.objects' && !identity(record, author)) continue;
      if (path === 'royalCouncil.members' && (prior || author) && !['kind', 'refId', 'party'].every(field => same(get(record, field), get(prior || author, field)))) continue;
      if (incoming && (prior || author) && allowedRecord(incoming, path)) merge(record, prior || {}, incoming, author || {}, path);
    }
    for (const record of release) {
      if (existing.has(record.id) || old.has(record.id) || authorKnown && seeds.has(record.id) || !allowedRecord(record, path)) continue;
      const adopted = clean(record, '', path);
      current.push(adopted); existing.set(record.id, adopted);
    }
    return current;
  }
  function merge(current, base, release, authored, path) {
    for (const [field, value] of Object.entries(release)) {
      if (field === 'id' || field === 'publicationRevision' || field === 'territoryGrid') continue;
      const childPath = child(path, field);
      if (path === 'royalCouncil' && ['influence', 'loyalty', 'pools', 'powerPool', 'loyaltyPool', 'influencePool'].includes(field) && own(current, field)) continue;
      if (path.startsWith('royalCouncil.members') && ['influence', 'loyalty', 'rating'].includes(field) && own(current, field)) continue;
      if (field === 'wallConstruction' || path === 'meta' && field === 'ferryNetwork') {
        // Intact ledgers/networks adopt atomically; custom choices stay literal.
        if (unchanged(current, base, authored, field)) set(current, field, clean(value, field, childPath));
        continue;
      }
      if (referenceField(path, field) && !validReference(field, value)) continue;
      if (field === 'owner' && referenceField(path, 'faction') && own(release, 'faction') && !validReference('faction', get(release, 'faction'))) continue;
      // A supplied seed's own crest proves prior presence without general author lineage.
      if (path === 'meta' && field === 'gilneasHeraldry' && own(authored, field) && !own(current, field)) continue;
      if ((own(base, field) || authorKnown && own(authored, field)) && !own(current, field)) continue;
      if (object(value) && object(get(current, field)) && (object(get(base, field)) || object(get(authored, field)))) {
        merge(get(current, field), get(base, field) || {}, value, get(authored, field) || {}, childPath);
      } else if (keyed(value) && keyed(get(current, field)) && (keyed(get(base, field)) || keyed(get(authored, field)))) {
        mergeArray(get(current, field), get(base, field) || [], value, get(authored, field) || [], childPath);
      } else if (unchanged(current, base, authored, field)) set(current, field, clean(value, field, childPath));
    }
  }
  for (const source of published.sources || []) {
    if (!sources.has(source.id) && !oldSources.has(source.id) && !(authorKnown && (seed.sources || []).some(record => record.id === source.id))) {
      result.sources ??= []; result.sources.push(structuredClone(source)); sources.set(source.id, result.sources.at(-1));
    }
  }
  const removed = new Set();
  const releases = index(published.locations);
  result.locations = (result.locations || []).filter(record => {
    const remove = oldLocations.has(record.id) && !releases.has(record.id) && same(record, oldLocations.get(record.id));
    if (remove) removed.add(record.id);
    return !remove;
  });
  for (const collection of ['factions', 'nobles', 'locations', 'sources']) {
    const old = index(previous[collection]), authored = index(seed[collection]), incoming = index(published[collection]);
    for (const record of result[collection] || []) {
      const release = incoming.get(record.id), base = old.get(record.id), author = authored.get(record.id);
      if (release && (base || eligible[collection]?.has(record.id))) merge(record, base || {}, release, author || {}, collection);
    }
    if (collection === 'sources') continue;
    const current = index(result[collection]);
    for (const record of published[collection] || []) {
      if (current.has(record.id) || !eligible[collection].has(record.id) || !allowedRecord(record, collection)) continue;
      result[collection] ??= []; result[collection].push(clean(record, '', collection));
    }
  }
  for (const record of result.locations) if (Array.isArray(record.linkedLocationIds) && removed.size) record.linkedLocationIds = record.linkedLocationIds.filter(id => !removed.has(id));
  result.meta ??= {};
  merge(result.meta, previous.meta || {}, published.meta || {}, seed.meta || {}, 'meta');
  if (own(published, 'royalCouncil')) {
    if (!own(result, 'royalCouncil') && !own(previous, 'royalCouncil') && !(authorKnown && own(seed, 'royalCouncil'))) result.royalCouncil = clean(published.royalCouncil, '', 'royalCouncil');
    else if (object(result.royalCouncil) && object(published.royalCouncil)) merge(result.royalCouncil, previous.royalCouncil || {}, published.royalCouncil, seed.royalCouncil || {}, 'royalCouncil');
  }
  // An explicit full-domain redraw replaces only an exact unchanged grid; a
  // painted cell, author extension or prior deletion remains an author choice.
  const fullRealmRedraw = published.territoryGrid?.migration?.method === 'author-full-realm-layout';
  const realmCompatible = published.meta?.image === result.meta?.image && published.meta?.mapRevision === result.meta?.mapRevision &&
    published.meta?.width === result.meta?.width && published.meta?.height === result.meta?.height &&
    published.territoryGrid?.keys?.every(id => (result.factions || []).some(f => f.id === id));
  const pristineAuthorGrid = own(draft, 'territoryGrid') && unchanged(draft, previous, seed, 'territoryGrid');
  const noPriorGrid = !own(draft, 'territoryGrid') && !own(previous, 'territoryGrid') && !own(seed, 'territoryGrid');
  if (own(published, 'territoryGrid') && (fullRealmRedraw ? realmCompatible && (pristineAuthorGrid || noPriorGrid) : noPriorGrid)) {
    result.territoryGrid = structuredClone(published.territoryGrid);
  }
  if (fullRealmRedraw && realmCompatible && same(published.territories, []) &&
      unchanged(draft, previous, seed, 'territories')) result.territories = [];
  result.meta.publicationRevision = revision;
  return result;
}
