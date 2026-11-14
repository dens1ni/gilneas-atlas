export function initChronicle(getData) {
  const $=id=>document.getElementById(id);
  let tab='history';
  function el(tag,text='',className='') {
    const e=document.createElement(tag);e.textContent=text;if(className)e.className=className;return e;
  }
  function sourceLinks(container,ids) {
    const sources=getData().sources||[];
    for(const id of ids||[]) {
      const s=sources.find(s=>String(s.id)===String(id));
      if(!s||!/^https?:\/\//i.test(s.url))continue;
      const a=el('a',`[${s.id}] ${s.title}`);a.href=s.url;a.target='_blank';a.rel='noopener noreferrer';container.append(a,el('br'));
    }
  }
  function render() {
    const body=$('chronicle-content'),data=getData();body.replaceChildren();
    for(const key of ['history','nobles','sources'])$('chronicle-'+key).classList.toggle('active',tab===key);
    if(tab==='history') {
      for(const section of data.meta.chronicle||[]) {
        const node=el('section','','chronicle-section');node.append(el('h3',section.title),el('p',section.text));sourceLinks(node,section.sources);body.append(node);
      }
      const note=el('section','','chronicle-section');
      note.append(el('h3','Как читать этот атлас'),el('p','Основной источник — Wowpedia. У каждой локации отдельно учитываются её существование, владение и датировка. Если имя владельца не установлено для выбранной эпохи, оно остаётся пустым. Поздно описанные места доступны как исторические реконструкции, а не как подтверждённые довоенные владения.\n\nЦветные области — начальная картографическая схема для сценария. Они редактируются независимо от досье и не выдаются за канонический кадастр. Дом Седогривов обозначает коронные земли внутри Гилнеаса; это не утверждение, что правящая династия является обычным феодальным вассалом.\n\nИсходный игровой рендер относится к более позднему состоянию мира. Видимые элементы стены и кратера адаптированы локальной ретушью; Даларан показан условной наземной городской виньеткой. Это картографическая реконструкция, не восстановленный довоенный снимок. Контуры берега и координатное пространство сохранены.'));
      body.append(note);
    } else if(tab==='nobles') {
      for(const noble of data.nobles||[]) {
        const node=el('section','','noble-card');node.id='noble-'+noble.id;node.append(el('h3',noble.name),el('span',noble.title||'','eyebrow'),el('p',noble.description||''));
        if(noble.periodNote||noble.note)node.append(el('small',noble.periodNote||noble.note));
        sourceLinks(node,noble.sources);body.append(node);
      }
    } else {
      const intro=el('section','','chronicle-section');intro.append(el('h3','Архив свидетельств'),el('p','Wowpedia используется как основной справочник. Цитаты ниже — фрагменты реально прочитанных страниц; английский оригинал сохранён для проверки. Когда использовано зеркало, источник обозначает это отдельно.'));body.append(intro);
      for(const s of data.sources||[]) {
        const section=el('section','','chronicle-section');section.id='source-'+s.id;section.append(el('h3',`[${s.id}] ${s.title}`));
        if(/^https?:\/\//i.test(s.url)) {const a=el('a',s.url);a.href=s.url;a.target='_blank';a.rel='noopener noreferrer';section.append(a);}
        if(s.canonicalUrl&&s.canonicalUrl!==s.url&&/^https?:\/\//i.test(s.canonicalUrl)){const p=el('p','Зеркало. Оригинал: '),a=el('a',s.canonicalUrl);a.href=s.canonicalUrl;a.target='_blank';a.rel='noopener noreferrer';p.append(a);section.append(p);}
        if(s.quote)section.append(el('blockquote',s.quote));
        if(s.note)section.append(el('p',s.note));body.append(section);
      }
    }
  }
  function open(which='history',id=null) {
    tab=which;render();
    document.querySelectorAll('dialog[open]').forEach(d=>d.close());
    $('chronicle').showModal();$('chronicle').focus();
    if(id)requestAnimationFrame(()=>{
      const node=document.getElementById((tab==='nobles'?'noble-':'source-')+id);
      if(node)$('chronicle').scrollTop=node.offsetTop-110;
    });
  }
  for(const key of ['history','nobles','sources'])$('chronicle-'+key).onclick=()=>{tab=key;render();};
  $('chronicle-open').onclick=()=>open();
  return {open,render};
}
