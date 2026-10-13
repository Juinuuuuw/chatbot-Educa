"""Indicadores de demanda sem guardar texto, áudio ou telefone nos relatórios."""
import datetime as dt
import hashlib
import json
import re
import unicodedata
from collections import Counter

LOCAL=dt.timezone(dt.timedelta(hours=-3))
TOPICS={
    'Inscrição e matrícula':r'inscri|matricul',
    'Gratuidade e valores':r'gratuit|mensalidade|taxa|preco|\bcusta|\bpago|\bpagar',
    'Dias e horários':r'horario|\bque horas|\bdias?\b|segunda|terca|quarta|quinta|sexta|sabado',
    'Vagas e novas turmas':r'\bvagas?\b|nova\w* turma|abertura|proxim\w* turma',
    'Documentos':r'document|\bcpf\b|identidade|comprovante|\blevar\b',
    'Participação e idade':r'idade|\banos\b|participar|quem pode',
    'Local das atividades':r'\bonde\b|endereco|localiz|local das aulas',
    'Certificado':r'certificad',
    'Cursos e atividades':r'\bcursos?\b|atividades|\bteatro\b|\bballet\b|\bbale\b|danca|musculacao|informatica|praticas corporais',
    'Atendimento da equipe':r'atendente|humano|falar com (?:alguem|uma pessoa|a equipe)',
}

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')

def classify(text):
    text=normalize(text)
    topics=[name for name,pattern in TOPICS.items() if re.search(pattern,text)]
    courses=[]
    if 'teatro' in text or 'maturidade' in text:
        if 'maturidade' in text: courses.append('Teatro na Maturidade')
        elif re.search(r'teatro\s+infantil',text): courses.append('Teatro Infantil')
        elif re.search(r'teatro\s+juvenil',text): courses.append('Teatro Juvenil')
        elif re.search(r'teatro\s+adulto\s+ii\b',text): courses.append('Teatro Adulto II')
        elif re.search(r'teatro\s+adulto\s+i\b',text): courses.append('Teatro Adulto I')
        else: courses.append('Teatro · turma não identificada')
    for name,pattern in [('Ballet',r'\bballet\b|\bbale\b'),('Dança Mix',r'danca\s+mix'),('Dança Contemporânea',r'danca\s+contemporanea'),('Musculação',r'musculacao'),('Práticas corporais',r'praticas\s+corporais'),('Informática',r'informatica')]:
        if re.search(pattern,text): courses.append(name)
    if 'danca' in text and not any(name.startswith('Dança') for name in courses): courses.append('Dança · modalidade não identificada')
    return topics,courses

def init(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS demand(id TEXT PRIMARY KEY, day TEXT, contact TEXT, audio INTEGER, topics TEXT, courses TEXT);
    CREATE TABLE IF NOT EXISTS handoffs(id TEXT PRIMARY KEY, day TEXT, reason TEXT);
    CREATE INDEX IF NOT EXISTS demand_day ON demand(day);
    ''')

def record_message(c,row):
    if row['role']!='contact': return
    topics,courses=classify(row['text'] or '')
    day=dt.datetime.fromtimestamp(row['created'],LOCAL).date().isoformat()
    key=hashlib.sha256((row['chat']+'|'+row['id']).encode()).hexdigest()
    contact=hashlib.sha256(row['chat'].encode()).hexdigest()
    c.execute('''INSERT INTO demand VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE
      SET topics=excluded.topics,courses=excluded.courses''', (key,day,contact,bool(row['mime']),json.dumps(topics,ensure_ascii=False),json.dumps(courses,ensure_ascii=False)))

def record_handoff(c,id,reason):
    day=dt.datetime.now(LOCAL).date().isoformat()
    key=hashlib.sha256(id.encode()).hexdigest()
    c.execute('INSERT OR IGNORE INTO handoffs VALUES (?,?,?)',(key,day,reason))

def report(c,days=7):
    today=dt.datetime.now(LOCAL).date()
    start=today-dt.timedelta(days=days-1)
    rows=c.execute('SELECT * FROM demand WHERE day>=? AND day<=?',(start.isoformat(),today.isoformat())).fetchall()
    events=c.execute('SELECT reason FROM handoffs WHERE day>=? AND day<=?',(start.isoformat(),today.isoformat())).fetchall()
    topics=Counter();courses=Counter();daily=Counter();audio_count=0
    for row in rows:
        topics.update(json.loads(row['topics']));courses.update(json.loads(row['courses']));daily[row['day']]+=1;audio_count+=row['audio']
    def ranking(values): return [{'name':name,'count':count} for name,count in sorted(values.items(),key=lambda item:(-item[1],item[0]))]
    return {'days':days,'start':start.isoformat(),'end':today.isoformat(),
        'totals':{'messages':len(rows),'contacts':len({r['contact'] for r in rows}),'audio':audio_count,'text':len(rows)-audio_count,'handoffs':len(events)},
        'topics':ranking(topics),'courses':ranking(courses),'handoff_reasons':ranking(Counter(r['reason'] for r in events)),
        'daily':[{'day':(start+dt.timedelta(days=i)).isoformat(),'count':daily[(start+dt.timedelta(days=i)).isoformat()]} for i in range(days)]}
