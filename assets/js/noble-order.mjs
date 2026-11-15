const isRecord = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const familyRoles = new Set(['father', 'mother', 'parent', 'child', 'son', 'daughter',
  'spouse', 'sibling', 'brother', 'sister']);
const byRating = (a, b) => b.rating - a.rating || a.index - b.index;

/**
 * Pure view ordering of the current full snapshot; filter the returned rows afterwards.
 * Returns a fresh array containing only the original snapshot.nobles references.
 *
 * Personal ratings are maximum valid integer kingdom values (0..100) from exact
 * person/refId Council rows. Missing/invalid ratings are view-only zero; active,
 * party, titles, age and registryPriority never imply influence or life status.
 *
 * Exact nonempty houses and existing explicit family IDs form connected groups.
 * Nondead groups rank by their nondead maximum, then first nondead source position;
 * each group's members rank by their own rating, then original source position.
 * Only literal lifeStatus === 'dead' goes to the final section. That section uses
 * the nondead family ranking when any nondead relative exists, otherwise the dead
 * maximum. Ties retain the family's first nondead position (first overall for an
 * all-dead group). Dead members retain the same individual-rating/source tie rule.
 *
 * No imports, normalization, guessed relationships, stored weights or input writes.
 * A missing/non-array nobles collection returns []; malformed/duplicate canonical
 * records throw TypeError instead of being repaired or silently dropped.
 *
 * @param {object} snapshot Current read-only atlas snapshot, including optional royalCouncil.
 * @returns {object[]} A mutable new array of canonical noble record references.
 */
export function orderNobles(snapshot) {
  if (!Array.isArray(snapshot?.nobles)) return [];
  const nobles = snapshot.nobles;
  const byId = new Map();
  for (const [index, noble] of nobles.entries()) {
    if (!isRecord(noble) || typeof noble.id !== 'string' || noble.id.length === 0) {
      throw new TypeError(`nobles[${index}]: ожидается запись с непустым строковым id`);
    }
    if (byId.has(noble.id)) throw new TypeError(`nobles: повтор id ${noble.id}`);
    byId.set(noble.id, index);
  }

  const ratings = new Map();
  const members = Array.isArray(snapshot.royalCouncil?.members) ? snapshot.royalCouncil.members : [];
  for (const member of members) {
    if (!isRecord(member) || member.kind !== 'person' || !byId.has(member.refId) ||
        !isRecord(member.influence)) continue;
    const kingdom = member.influence.kingdom;
    if (Number.isInteger(kingdom) && kingdom >= 0 && kingdom <= 100) {
      ratings.set(member.refId, Math.max(ratings.get(member.refId) ?? 0, kingdom));
    }
  }

  // Union-find is local only; dead relatives can connect a family but never rate its living members.
  const parents = nobles.map((_, index) => index);
  const root = index => {
    while (parents[index] !== index) {
      parents[index] = parents[parents[index]];
      index = parents[index];
    }
    return index;
  };
  const join = (index, id) => {
    if (byId.has(id)) parents[root(byId.get(id))] = root(index);
  };
  const houses = new Map();
  nobles.forEach((noble, index) => {
    if (typeof noble.house === 'string' && noble.house.length > 0) {
      if (houses.has(noble.house)) join(index, houses.get(noble.house));
      else houses.set(noble.house, noble.id);
    }
    for (const relation of Array.isArray(noble.relations) ? noble.relations : []) {
      if (isRecord(relation) && familyRoles.has(relation.relation)) join(index, relation.nobleId);
    }
    if (isRecord(noble.spouse)) join(index, noble.spouse.nobleId);
  });

  const groups = new Map();
  nobles.forEach((noble, index) => {
    const row = { noble, index, rating: ratings.get(noble.id) ?? 0 };
    const key = root(index);
    let group = groups.get(key);
    if (!group) {
      group = { index, rating: 0, deadRating: 0, livingIndex: null, living: [], dead: [] };
      groups.set(key, group);
    }
    if (noble.lifeStatus === 'dead') {
      group.deadRating = Math.max(group.deadRating, row.rating);
      group.dead.push(row);
    } else {
      group.rating = Math.max(group.rating, row.rating);
      group.livingIndex ??= index;
      group.living.push(row);
    }
  });

  const families = [...groups.values()];
  const living = families.filter(group => group.living.length > 0)
    .sort((a, b) => b.rating - a.rating || a.livingIndex - b.livingIndex)
    .flatMap(group => group.living.sort(byRating).map(row => row.noble));
  const deadScore = group => group.living.length > 0 ? group.rating : group.deadRating;
  const familyPosition = group => group.livingIndex ?? group.index;
  const dead = families.filter(group => group.dead.length > 0)
    .sort((a, b) => deadScore(b) - deadScore(a) || familyPosition(a) - familyPosition(b))
    .flatMap(group => group.dead.sort(byRating).map(row => row.noble));
  return [...living, ...dead];
}
