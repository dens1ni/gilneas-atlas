"""Final display-only source cleanup; preserve identities and citations."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'assets/data/atlas.json'
data=json.loads(path.read_text())
link=re.compile(r'\[([^\]]*)\]\((?:[^()\s]|\([^()]*\))*\)')
for source in data['sources']:
 text=source['quote']
 text=link.sub(r'\1',text)
 text=re.sub(r'\[\[\s*(\d+)\s*\]\]\(\)',r'[\1]',text)
 text=re.sub(r'\[\[([^\]]+)\]\]\([^)]*\)',r'[\1]',text)
 text=text.replace('**','').replace('_','').replace('`','')
 source['quote']=text
 if 'wago.tools' in source['url']:source['title']='Игровая локализация ruRU · AreaTable'
 if 'worldofwarcraft.blizzard.com/ru-ru/media/short-story/' in source['url']:source['title']='Blizzard · Вожак стаи (русский текст)'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'locations':len(data['locations']),'nobles':len(data['nobles']),'sources':len(data['sources']),'objects':sum(len(l['objects']) for l in data['locations'])},ensure_ascii=False))
