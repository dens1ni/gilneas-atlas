"""Merge retrieved lore with coordinate anchors; never infer private tenure."""
import json,re,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRATCH=Path('/Users/daniil_si/.hermes/cache/scratch')
base=json.loads((ROOT/'assets/data/atlas.json').read_text())
location_research=json.loads((SCRATCH/'gilneas-research-locations.json').read_text())
noble_research=json.loads((SCRATCH/'gilneas-research-nobles.json').read_text())
coords=json.loads((ROOT/'scripts/coordinates.json').read_text())['locations']


def readable(text):
 text=html.unescape(text or '')
 text=re.sub(r'!?\[([^\]]*)\]\((?:[^()\s]|\([^()]*\))*\)',r'\1',text)
 text=re.sub(r'(?m)^#{1,6}\s*','',text)
 text=text.replace('**','').replace('__','')
 return text.strip()

# Source identity is URL-based; independently collected ledgers do not collide.
sources=[];url_ids={};evidence_checks=[]
def source(e):
 url=e.get('url') or e.get('retrieved_url')
 if not url:return None
 canonical=e.get('canonical_wowpedia_url') or e.get('preferred_article_url') or e.get('canonical_url') or url
 identity=canonical if canonical.startswith('https://wowpedia.fandom.com/wiki/') and url.startswith('https://wowpedia.fandom.com/wiki/') else url
 quote=e.get('readable_quote') or e.get('supporting_quote') or e.get('quote') or ''
 if not quote and e.get('quotes'):quote=e['quotes'][0]
 quote=readable(quote)
 if identity not in url_ids:
  sid=len(sources)+1;url_ids[identity]=sid
  s={'id':sid,'title':e.get('title') or identity.rsplit('/',1)[-1].replace('_',' '),'url':url,'canonicalUrl':canonical,'quote':quote}
  if 'wiki.gg' in url:s['note']='Зеркало Warcraft Wiki; основной оригинал — Wowpedia.'
  if e.get('provider')=='Wowhead' or 'wago.tools' in url:s['note']='Игровая локализация: подтверждает написание имени, не довоенную датировку.'
  sources.append(s)
 else:
  sid=url_ids[identity];s=sources[sid-1]
  if not s['quote'] and quote:s['quote']=quote
 path=e.get('evidence_path') or e.get('snapshot_path')
 evidence_checks.append({'source':sid,'path':path,'quote':e.get('supporting_quote') or e.get('quote') or quote,'declaredVerified':e.get('quote_verified',False)})
 return sid

def refs(evidence):
 return list(dict.fromkeys(s for e in evidence for s in [source(e)] if s))

location_map={
 'gilneas-city':'gilneas_city','cathedral-quarter':'gilneas_cathedral_quarter','lights-dawn-cathedral':'gilneas_lights_dawn_cathedral','greymane-court':'gilneas_greymane_court','merchant-square':'gilneas_merchant_square','military-district':'gilneas_military_district','stoneward-prison':'gilneas_stoneward_prison','greymane-manor':'gilneas_greymane_manor','keel-harbor':'gilneas_keel_harbor','duskhaven':'gilneas_duskhaven','crowley-orchard':'gilneas_crowley_orchard','crowley-stable-grounds':'gilneas_crowley_stables','hayward-fishery':'gilneas_hayward_fishery','hammond-farmstead':'gilneas_hammond_farmstead','allen-farmstead':'gilneas_allen_farmstead','emberstone-village':'gilneas_emberstone_village','emberstone-mine':'gilneas_emberstone_mine','stormglen':'gilneas_stormglen','blackwald':'gilneas_blackwald','taldoren':'gilneas_taldoren','bradshaw-mill':'gilneas_bradshaw_mill','tempests-reach':'gilneas_tempests_reach','aderics-repose':'gilneas_aderics_repose','northgate-woods':'gilneas_northgate_woods','northgate-river':'gilneas_northgate_river','northern-headlands':'gilneas_northern_headlands','the-headlands':'gilneas_headlands','pyrewood':'gilneas_pyrewood','shadowfang':'gilneas_silverlaine_keep','ambermill':'gilneas_ambermill','dalaran-city':'dalaran_city','fenris-keep':'fenris_keep','fenris-isle':'fenris_isle','lordaeron-city':'lordaeron_capital_city','silverpine':'silverpine_forest'}
research_by={l['id']:l for l in location_research['locations']}
for l in base['locations']:
 r=research_by[location_map[l['id']]]
 oldname=l['name'];name=r['name_ru']
 if l['id']=='gilneas-city':name='Город Гилнеас'
 if l['id']=='shadowfang':name='Крепость над Пирвудом'
 l['name']=name;l['englishName']=r['name_en'];l['aliases']=list(dict.fromkeys([oldname,*r.get('aliases',[])]))
 state=r['pre_wall_existence']['status']
 # Positive existence and private-title evidence are independent.
 known=state in ['confirmed','confirmed_historical_lake','confirmed_ancient_citadel']
 if l['id']=='blackwald':known=True # Primary Lord of His Pack's early court hunts, below.
 l['provenance']['confidence']='confirmed' if known else 'reconstruction'
 l['provenance']['sources']=refs(r.get('evidence',[]))
 l['provenance']['chronology']=r['pre_wall_existence']['note']
 l['provenance']['note']=r['notes_ru'] if not known else ''
 l['provenance']['historicalAffiliation']=r['known_historical_or_later_affiliation']
 l['provenance']['ownerStatus']='confirmed' if l['id'] in ['gilneas-city','pyrewood','ambermill','dalaran-city','lordaeron-city'] else 'unknown'
 if l['provenance']['ownerStatus']=='unknown':l['owner']=''
 if r.get('name_evidence'):
  l['provenance']['sources']=list(dict.fromkeys(l['provenance']['sources']+refs([r['name_evidence']])))
  l['provenance']['nameStatus']=r['name_status']
 # Keep introductory text fluent while retaining exact canonical names.
 for old,new in [('Сумеречной гавани','Темной Гавани'),('Сумеречная гавань','Темная Гавань'),('Углестона','Тлеющего Угля'),('Штормглена','Грозового Перевала'),('Штормглен','Грозовой Перевал'),('Чёрного леса','Черной дубравы')]:l['description']=l['description'].replace(old,new)
 if l['id']=='greymane-manor':l['description']='Резиденция семьи Седогривов высоко в западных холмах, известная из более поздних источников. Точная дата основания поместья и имя владельца именно до стены не подтверждены. Показано как реконструкция коронного района.'
 if l['id']=='greymane-court':l['description']='Юго-западный квартал Гилнеаса, названный в честь правящей семьи. Его планировка и название засвидетельствованы поздней игровой картой; частный владелец в выбранную эпоху не установлен.'
 if l['id']=='blackwald':l['description']='Южная лесная область Гилнеаса и место королевских охот. В ранней истории здесь охотились Генн, Эшбери, Годфри и Марли. Поздние культы и воргенские лагеря не перенесены в этот период.'
 if l['id']=='shadowfang':
  l['description']='Каменная крепость на возвышенности над Пирвудом. Во вторичной истории её лорды подчинены семье Краули; барон Сребролен владел замком до Аругала. Однако его владение именно до постройки стены отдельно не датировано, поэтому имя владельца в текущем срезе не установлено.'
  l['provenance']['note']='Сребролен — позднее засвидетельствованный хозяин; точная довоенная дата неизвестна. Название «Тёмный Клык» позднее. Вассальная связь с Краули сохранена как сценарная реконструкция вторичного свидетельства.'
 if l['id']=='taldoren':
  l['description']='Древнее дерево Черной дубравы. Показано как природный ориентир, не как действующее поселение ночных эльфов. Сведения о его связи с Друидами Стаи расходятся в источниках; отражение в Изумрудном Сне не является второй точкой на этой карте.'
 if l['id']=='dalaran-city':l['owner']='Совет Шести · Антонидас'
 if l['id']=='lordaeron-city':l['owner']='Теренас Менетил II'
 if l['faction'] is None:l['provenance']['affiliationStatus']='unknown'

# Add the remaining major landmarks covered by the selected stage without
# inventing a Crowley manor or adding later war camps.
for id,rid,name,faction,owner,type in [
 ('lordamere-lake','lordamere_lake','Озеро Лордамер',None,'','landmark'),
 ('deep-elem-mine','silverpine_deep_elem_mine','Серебряный рудник','lordaeron','','mine'),
 ('galewatch-lighthouse','gilneas_galewatch_lighthouse','Штормовой маяк','gilneas','','landmark')]:
 r=research_by[rid];e=refs(r.get('evidence',[]));known=r['pre_wall_existence']['status']=='confirmed_historical_lake';p={'confidence':'confirmed' if known else 'reconstruction','sources':e,'note':r['notes_ru'],'ownerStatus':'unknown','chronology':r['pre_wall_existence']['note']}
 if faction is None:p['affiliationStatus']='unknown'
 base['locations'].append({'id':id,'name':name,**coords[id],'type':type,'faction':faction,'owner':owner,'englishName':r['name_en'],'description':{'lordamere-lake':'Большое озеро между северными королевствами. На его берегах находятся земли Лордерона, Даларана и Альтерака; весь водоём не назначен единому частному владельцу.','deep-elem-mine':'Рудник в Серебряном бору. Он известен до воргенского захвата, но отдельное довоенное владение до стены не установлено. Не назначен Марли или Краули на основании соседства.','galewatch-lighthouse':'Маяк восточного побережья у Предела бури. Дата основания и распорядитель в эпоху до стены не установлены.'}[id],'objects':[],'provenance':p})
r=research_by['dalaran_violet_citadel'];base['locations'].append({'id':'violet-citadel','name':r['name_ru'],'x':2875,'y':1480,'type':'fortress','faction':'dalaran','owner':'Кирин-Тор','description':'Аметистовая цитадель — древняя крепость и средоточие Кирин-Тора, где сосредоточены библиотеки заклинаний и исследовательские лаборатории. Внутренние помещения можно занести в объекты досье; план Нордскола не выдаётся за точный довоенный чертёж.','objects':[],'provenance':{'confidence':'confirmed','sources':refs(r['evidence']),'note':'Расположение на городской виньетке условное; сам древний объект подтверждён.'}})

# Research knows more nobles but foreign claimants are not fictional landholders.
nsource={s['id']:s for s in noble_research['sources']}
oldn={n['id'].removeprefix('noble-'):n for n in base['nobles']}
ids={'genn-greymane':'genn','darius-crowley':'darius','vincent-godfrey':'godfrey','baron-ashbury':'ashbury','lord-marley':'marley','archibald-greymane':'archibald','lord-ashbury-first':'ashbury-first','lord-walden':'walden','lord-hewell':'hewell','baron-silverlaine':'silverlaine','baron-longshore':'longshore','lord-candren':'candren','isiden-perenolde':'isiden'}
nobles=[]
for n in noble_research['nobles']:
 if n['id'] not in ids:continue
 key=ids[n['id']];old=oldn.get(key,{})
 title=old.get('title') or {'archibald':'Прежний король Гилнеаса','ashbury-first':'Советник Арчибальда · отец барона Эшбери','isiden':'Альтеракский претендент · гость Гилнеаса'}[key]
 confidence='confirmed' if n.get('display_in_pre_wall_court') or key in ['archibald','ashbury-first','isiden'] else 'reconstruction'
 srefs=refs([nsource[sid] for sid in n['source_ids'] if sid in nsource])
 name=n['name_ru']
 if key=='longshore':name='Барон Дольноберег';
 nobles.append({'id':'noble-'+key,'name':name,'englishName':n['name_en'],'title':title,'description':n['safe_text_ru'],'periodNote':n['limits_ru'],'sources':srefs,'house':old.get('house'),'confidence':confidence,'role':n['role_for_map'],'provenance':{'confidence':confidence,'sources':srefs}})
# Names not explored by this noble sweep retain the fetched main catalogue;
# they remain late references with unknown holdings.
for key in ['tulvan','harford','morrison','aderic']:
 old=oldn[key];e=[next(s for s in noble_research['sources'] if 'Nobles_of_Gilneas' in s['url'])];old['sources']=refs(e);old['provenance']['sources']=old['sources'];nobles.append(old)
base['nobles']=nobles

# Primary early-hunt evidence augments Blackwald without silently accepting
# the unverified date of a late locale article.
primary=next(s for s in noble_research['sources'] if s.get('retrieval_method')=='browser_dom_full_story')
black=next(l for l in base['locations'] if l['id']=='blackwald');black['provenance']['sources']=list(dict.fromkeys(black['provenance']['sources']+refs([primary,nsource[288]])))

# Every group and polygon points into the same URL-owned ledger.
main_nobles=next(s for s in noble_research['sources'] if 'Nobles_of_Gilneas' in s['url'])
main_gilneas=research_by['gilneas_kingdom'];main_dalaran=research_by['dalaran_city'];main_lordaeron=research_by['lordaeron_capital_city']
for f in base['factions']:
 evid=main_gilneas['evidence'] if f['id']=='gilneas' else main_dalaran['evidence'] if f['id']=='dalaran' else main_lordaeron['evidence'] if f['id']=='lordaeron' else [main_nobles]
 f['provenance']['sources']=refs(evid);f['provenance']['confidence']='reconstruction' if f['id'] in ['silverlaine','walden'] else 'confirmed'
 if f['id']=='silverlaine':f['name']='Дом Сребролена';f['ruler']='';f['description']='Вассальная связь с Краули и титул барона засвидетельствованы вторичной поздней историей; довоенная дата не установлена. Это отдельный сценарный дом, не доказанный кадастр до стены.'
 if f['id']=='walden':f['provenance']['note']='Титул и земли до стены неизвестны.'
for t in base['territories']:
 r=research_by['gilneas_ambermill'] if t['faction']=='crowley' else main_dalaran if t['faction']=='dalaran' else research_by['fenris_keep'] if 'fenris' in t['id'] else main_gilneas
 t['provenance']['sources']=refs(r['evidence'])
for i,ch in enumerate(base['meta']['chronicle']):
 evid=research_by['gilneas_ambermill']['evidence'] if i==1 else [nsource[285],nsource[288]] if i==0 else location_research['chronology'][0]['evidence'] if i==2 else [main_nobles,nsource[289]]
 ch['sources']=refs(evid)
base['meta']['sourceMethod']='Wowpedia primary; Blizzard corroboration; names verified separately against ruRU client data. No coordinates or unknown private estates derived from wiki speculation.'
base['meta']['researchCounts']={'locationsResearched':len(location_research['locations']),'noblesResearched':len(noble_research['nobles']),'supportedCanonicalOwnershipPolygons':0}
base['sources']=sources
(ROOT/'assets/data/atlas.json').write_text(json.dumps(base,ensure_ascii=False,indent=2)+'\n')
(ROOT/'docs/source-verification.json').write_text(json.dumps(evidence_checks,ensure_ascii=False,indent=2))
print(json.dumps({'locations':len(base['locations']),'nobles':len(nobles),'sources':len(sources),'factions':len(base['factions']),'territories':len(base['territories'])},ensure_ascii=False))
