"""Atualiza o RAG apenas com o edital e páginas oficiais da UERN."""
import json, re, hashlib, pathlib, shutil, datetime, concurrent.futures, argparse
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT=pathlib.Path(__file__).resolve().parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
PDF=DATA/'uern-educa-0192026edital.pdf'
TAG='https://portal.uern.br/blog/tag/educa/'
SESSION=requests.Session()
SESSION.headers['User-Agent']='EducaRAG/0.1 (prototipo academico)'

def get(url):
    r=SESSION.get(url,timeout=45); r.raise_for_status()
    if not r.url.startswith('https://portal.uern.br/'): raise ValueError('Origem não permitida')
    return BeautifulSoup(r.content,'html.parser')

def split(text,size=1400):
    text=re.sub(r'[ \t]+',' ',text)
    paras=[p.strip() for p in text.splitlines() if p.strip()]
    chunks=[]; buf=''
    for p in paras:
        if len(buf)+len(p)>size and buf:
            chunks.append(buf); buf=buf[-180:]+'\n'
        buf+=p+'\n'
    if buf.strip(): chunks.append(buf.strip())
    return chunks

def fetch_article(url):
    soup=get(url)
    title=soup.find('h1'); title=title.get_text(' ',strip=True) if title else url
    node=soup.select_one('.elementor-widget-theme-post-content') or soup.select_one('.entry-content') or soup.find('article')
    if not node: raise ValueError('Conteúdo principal ausente')
    for el in node.select('script,style,nav,footer,form'): el.decompose()
    text=node.get_text('\n',strip=True)
    date=soup.select_one('meta[property="article:published_time"]')
    date=date.get('content','')[:10] if date else ''
    if not date:
        for script in soup.select('script[type="application/ld+json"]'):
            match=re.search(r'"datePublished"\s*:\s*"([^"T]+)',script.get_text())
            if match: date=match.group(1); break
    if not date:
        months={'janeiro':1,'fevereiro':2,'março':3,'abril':4,'maio':5,'junho':6,'julho':7,'agosto':8,'setembro':9,'outubro':10,'novembro':11,'dezembro':12}
        header=soup.get_text(' ',strip=True)
        match=re.search(r'(\d{1,2}) de ('+'|'.join(months)+r') de (20\d{2})',header)
        if match: date=f'{int(match[3]):04d}-{months[match[2]]:02d}-{int(match[1]):02d}'
    return {'title':title,'url':url,'date':date,'kind':'site','text':text}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=pathlib.Path, default=PDF)
    source_pdf = parser.parse_args().pdf
    docs=[]; failures=[]
    if source_pdf.resolve() != PDF.resolve():
        shutil.copy2(source_pdf, PDF)
    reader=PdfReader(PDF)
    for i,page in enumerate(reader.pages):
        docs.append({'title':'Edital 019/2026 — semestre 2026.2','url':PDF.name,'date':'2026-07-23','kind':'edital','page':i+1,'text':page.extract_text(extraction_mode='layout')})
    soup=get(TAG)
    links=[]
    for a in soup.select('h2 a,h3 a'):
        u=a.get('href','')
        if u.startswith('https://portal.uern.br/blog/') and '/tag/' not in u and u not in links: links.append(u)
    for u in ['https://portal.uern.br/blog/educa-proex-divulga-programacao-de-semana-setembro-amarelo-de-21-a-25-09-no-campus-de-natal/','https://portal.uern.br/blog/uern-natal-oferta-mais-de-430-vagas-em-cursos-e-atividades-gratuitas/']:
        if u not in links: links.append(u)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(fetch_article,u):u for u in links[:14]}
        for f in concurrent.futures.as_completed(jobs):
            try: docs.append(f.result())
            except Exception as e: failures.append({'url':jobs[f],'error':str(e)})
    chunks=[]
    for doc in docs:
        for part in split(doc['text']):
            item={k:v for k,v in doc.items() if k!='text'}
            item['text']=part
            item['id']=hashlib.sha256((doc['url']+str(doc.get('page',''))+part).encode()).hexdigest()[:16]
            chunks.append(item)
    (DATA/'documents.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf-8')
    (DATA/'chunks.json').write_text(json.dumps(chunks,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'documents':len(docs),'chunks':len(chunks),'failures':failures,'scope':'Edital fornecido e artigos da primeira página da tag Educa; não é todo o arquivo histórico.'}
    (DATA/'ingestion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__': main()
