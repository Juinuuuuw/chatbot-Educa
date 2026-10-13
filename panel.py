"""Painel local e fila de transporte, independente da conexão com WhatsApp."""
import base64
import datetime
import json
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from analytics import init as init_analytics, record_message, record_handoff, report

def create_panel(root, token, generate, transcribe):
    panel = FastAPI(docs_url=None, redoc_url=None)
    @panel.middleware('http')
    async def privacy_headers(request, call_next):
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response
    db_path = Path(root) / 'data/panel.sqlite3'
    assets = Path(root) / 'panel'
    sessions, tickets = {}, {}
    session_lock = threading.Lock()

    @contextmanager
    def db():
        connection = sqlite3.connect(db_path, timeout=20)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY, label TEXT, state TEXT DEFAULT 'lia',
          revision INTEGER DEFAULT 0, owner TEXT DEFAULT '', reason TEXT DEFAULT '', updated REAL, started REAL);
        CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, chat TEXT, role TEXT, text TEXT,
          audio TEXT DEFAULT '', mime TEXT DEFAULT '', status TEXT, created REAL, revision INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS batches(id TEXT PRIMARY KEY, chat TEXT, status TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS connection(id INTEGER PRIMARY KEY, heartbeat REAL, error TEXT);
        CREATE INDEX IF NOT EXISTS msg_chat ON messages(chat,created);
        ''')
        init_analytics(c)
        for row in c.execute("SELECT * FROM messages WHERE role='contact'").fetchall():
            record_message(c,row)

    def check_origin(request):
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            raise HTTPException(403, 'Origem não autorizada.')

    def bridge(request: Request):
        supplied = request.headers.get('x-educa-token', '')
        if not secrets.compare_digest(supplied, token):
            raise HTTPException(401, 'Extensão não autorizada.')

    def user(request: Request):
        check_origin(request)
        sid = request.cookies.get('lia_panel', '')
        with session_lock:
            if sessions.get(sid, 0) < time.time():
                raise HTTPException(401, 'Entre pelo botão Abrir painel na extensão.')

    @panel.get('/')
    def index():
        return FileResponse(assets / 'index.html', headers={'Cache-Control': 'no-store'})

    @panel.get('/assets/{filename}')
    def asset(filename: str):
        if filename not in ['app.js', 'reports.js', 'style.css', 'educa-logo.png','educa-logo-dark.png']:
            raise HTTPException(404)
        return FileResponse(assets / filename)

    class Ticket(BaseModel):
        ticket: str = Field(max_length=100)

    @panel.post('/bridge/ticket', dependencies=[Depends(bridge)])
    def ticket():
        value = secrets.token_urlsafe(32)
        with session_lock:
            now = time.time()
            for old in list(tickets):
                if tickets[old] < now: tickets.pop(old, None)
            tickets[value] = now + 30
        return {'ticket': value}

    @panel.post('/session')
    def login(body: Ticket, request: Request, response: Response):
        check_origin(request)
        with session_lock:
            if tickets.pop(body.ticket, 0) < time.time():
                raise HTTPException(401, 'Acesso expirou. Abra o painel novamente pela extensão.')
            sid = secrets.token_urlsafe(32)
            sessions[sid] = time.time() + 28800
        response.set_cookie('lia_panel', sid, httponly=True, samesite='strict', max_age=28800)
        return {'ok': True}

    @panel.delete('/session', dependencies=[Depends(user)])
    def logout(request: Request, response: Response):
        with session_lock: sessions.pop(request.cookies.get('lia_panel'), None)
        response.delete_cookie('lia_panel')
        return {'ok': True}

    def expire(c):
        now = time.time()
        # Um processo encerrado durante envio não autoriza repeti-lo.
        stale = c.execute("SELECT chat FROM messages WHERE status='sending' AND created<?", (now-360,)).fetchall()
        for row in stale:
            c.execute("UPDATE chats SET state='waiting',revision=revision+1,reason='Envio incerto. Confira o WhatsApp antes de continuar.',updated=? WHERE id=?", (now,row['chat']))
        c.execute("UPDATE messages SET status='uncertain' WHERE status='sending' AND created<?", (now-360,))
        c.execute("DELETE FROM messages WHERE created<? AND status NOT IN ('queued','sending')", (now-86400,))
        c.execute('DELETE FROM batches WHERE created<?', (now-86400,))
        cutoff=(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))-datetime.timedelta(days=90)).date().isoformat()
        c.execute('DELETE FROM demand WHERE day<?',(cutoff,))
        c.execute('DELETE FROM handoffs WHERE day<?',(cutoff,))

    @panel.get('/api/reports', dependencies=[Depends(user)])
    def reports(days: int=7):
        if days not in [1,7,30,90]: raise HTTPException(422,'Escolha hoje, 7, 30 ou 90 dias.')
        with db() as c:
            expire(c)
            return report(c,days)

    @panel.get('/api/snapshot', dependencies=[Depends(user)])
    def snapshot():
        with db() as c:
            expire(c)
            chats = [dict(r) for r in c.execute('''SELECT c.*,
              (SELECT text FROM messages WHERE chat=c.id ORDER BY created DESC LIMIT 1) preview,
              (SELECT COUNT(*) FROM messages WHERE chat=c.id AND role='contact') messages
              FROM chats c ORDER BY updated DESC''')]
            connection = c.execute('SELECT * FROM connection WHERE id=1').fetchone()
        return {'chats': chats, 'connection': {'online': bool(connection and time.time()-connection['heartbeat']<20),
            'error': connection['error'] if connection else '', 'last_seen': connection['heartbeat'] if connection else None}}

    @panel.get('/api/messages', dependencies=[Depends(user)])
    def messages(chat: str):
        with db() as c:
            return [dict(r) for r in c.execute('SELECT id,chat,role,text,mime,status,created FROM messages WHERE chat=? ORDER BY created,id LIMIT 500', (chat,))]

    @panel.get('/api/audio', dependencies=[Depends(user)])
    def audio(id: str):
        with db() as c: row = c.execute('SELECT audio,mime FROM messages WHERE id=?', (id,)).fetchone()
        if not row or not row['audio']: raise HTTPException(404, 'Áudio indisponível.')
        return Response(base64.b64decode(row['audio']), media_type=row['mime'], headers={'Cache-Control':'no-store'})

    class Action(BaseModel):
        chat: str = Field(min_length=1, max_length=150)
        action: str
        owner: str = Field(default='Equipe EdUCA', min_length=1, max_length=60)

    @panel.post('/api/action', dependencies=[Depends(user)])
    def action(body: Action):
        states = {'take':'human', 'return':'lia', 'close':'closed', 'queue':'waiting'}
        if body.action not in states: raise HTTPException(422, 'Ação inválida.')
        with db() as c:
            if not c.execute('SELECT id FROM chats WHERE id=?', (body.chat,)).fetchone(): raise HTTPException(404)
            c.execute("UPDATE messages SET status='cancelled' WHERE chat=? AND role='lia' AND status='queued'", (body.chat,))
            if body.action in ['return','close']:
                c.execute("UPDATE messages SET status='cancelled' WHERE chat=? AND role='human' AND status='queued'", (body.chat,))
            c.execute("UPDATE chats SET state=?,revision=revision+1,owner=?,reason='',updated=? WHERE id=?", (states[body.action], body.owner if body.action=='take' else '',time.time(),body.chat))
        return {'ok': True}

    class Reply(BaseModel):
        chat: str = Field(min_length=1, max_length=150)
        text: str = Field(default='', max_length=4000)
        audio_base64: str = Field(default='', max_length=17_000_000)
        audio_mime: str = 'audio/webm'

    @panel.post('/api/reply', dependencies=[Depends(user)])
    def reply(body: Reply):
        if not body.text.strip() and not body.audio_base64: raise HTTPException(422,'Escreva ou grave uma mensagem.')
        if body.audio_base64:
            if body.audio_mime.split(';')[0] not in ['audio/webm','audio/ogg','audio/mp4','audio/wav']: raise HTTPException(422,'Formato de áudio inválido.')
            try: raw = base64.b64decode(body.audio_base64,validate=True)
            except (ValueError, base64.binascii.Error): raise HTTPException(422,'Áudio inválido.')
            if len(raw)>12*1024*1024: raise HTTPException(422,'Áudio maior que 12 MB.')
        with db() as c:
            row = c.execute('SELECT state,revision FROM chats WHERE id=?', (body.chat,)).fetchone()
            if not row or row['state']!='human': raise HTTPException(409,'Assuma a conversa antes de responder.')
            id = secrets.token_hex(16)
            c.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?)', (id,body.chat,'human',body.text.strip(),body.audio_base64,body.audio_mime if body.audio_base64 else '', 'queued',time.time(),row['revision']))
            c.execute('UPDATE chats SET updated=? WHERE id=?',(time.time(),body.chat))
        return {'id': id}

    class Register(BaseModel):
        chat: str = Field(min_length=1,max_length=150)
        label: str = Field(min_length=1,max_length=150)

    @panel.post('/bridge/register', dependencies=[Depends(bridge)])
    def register(body: Register):
        if not body.chat.endswith(('@c.us','@lid')): raise HTTPException(422,'Apenas conversas individuais.')
        with db() as c:
            c.execute("INSERT INTO chats(id,label,updated,started) VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET label=excluded.label", (body.chat,body.label,time.time(),time.time()))
        return {'ok': True}

    class Incoming(BaseModel):
        chat: str = Field(min_length=1,max_length=150)
        id: str = Field(min_length=1,max_length=250)
        text: str = Field(default='',max_length=4000)
        audio_base64: str = Field(default='',max_length=17_000_000)
        from_me: bool = False

    @panel.post('/bridge/incoming', dependencies=[Depends(bridge)])
    def incoming(body: Incoming):
        if body.audio_base64:
            try: raw = base64.b64decode(body.audio_base64,validate=True)
            except (ValueError, base64.binascii.Error): raise HTTPException(422,'Áudio inválido.')
            if len(raw)>12*1024*1024: raise HTTPException(422,'Áudio maior que 12 MB.')
        with db() as c:
            row = c.execute('SELECT * FROM chats WHERE id=?',(body.chat,)).fetchone()
            if not row: raise HTTPException(404,'Conversa não autorizada.')
            result=c.execute('INSERT OR IGNORE INTO messages VALUES (?,?,?,?,?,?,?,?,?)', (body.id,body.chat,'human' if body.from_me else 'contact',body.text,body.audio_base64,'audio/ogg' if body.audio_base64 else '', 'sent',time.time(),row['revision']))
            if result.rowcount:
                record_message(c,c.execute('SELECT * FROM messages WHERE id=?',(body.id,)).fetchone())
                if body.from_me:
                    c.execute("UPDATE chats SET state='human',revision=revision+1,owner='WhatsApp',updated=? WHERE id=?",(time.time(),body.chat))
                    c.execute("UPDATE messages SET status='cancelled' WHERE chat=? AND role='lia' AND status='queued'",(body.chat,))
                else:
                    c.execute("UPDATE chats SET state=CASE WHEN state='closed' THEN 'lia' ELSE state END,updated=? WHERE id=?",(time.time(),body.chat))
        return {'ok': True}

    class Batch(BaseModel):
        chat: str = Field(min_length=1,max_length=150)
        id: str = Field(min_length=1,max_length=250)
        ids: list[str] = Field(min_length=1,max_length=20)

    @panel.post('/bridge/batch', dependencies=[Depends(bridge)])
    def batch(body: Batch):
        with db() as c:
            chat=c.execute('SELECT * FROM chats WHERE id=?',(body.chat,)).fetchone()
            if not chat: raise HTTPException(404)
            if not c.execute('INSERT OR IGNORE INTO batches VALUES (?,?,?,?)',(body.id,body.chat,'processing',time.time())).rowcount: return {'ok':True,'duplicate':True}
            rows=[]
            for id in body.ids:
                row=c.execute("SELECT * FROM messages WHERE id=? AND chat=? AND role='contact'",(id,body.chat)).fetchone()
                if not row: raise HTTPException(422,'Mensagem não recebida nesta conversa.')
                rows.append(dict(row))
        timer = None
        finished = threading.Event()
        def waiting_clip():
            if finished.is_set(): return
            manifest=assets.parent/'assets/waiting/manifest.json'
            if not manifest.exists(): return
            clips=json.loads(manifest.read_text(encoding='utf-8'))
            if not clips: return
            clip=secrets.choice(clips)
            filename=Path(clip['file']).name
            if not filename.startswith('waiting-') or not filename.endswith('.ogg'): return
            raw=(manifest.parent/filename).read_bytes()
            with db() as c:
                current=c.execute('SELECT state,revision FROM chats WHERE id=?',(body.chat,)).fetchone()
                if not finished.is_set() and current['state']=='lia' and current['revision']==chat['revision']:
                    c.execute('INSERT OR IGNORE INTO messages VALUES (?,?,?,?,?,?,?,?,?)',('wait:'+body.id,body.chat,'lia',clip['text'],base64.b64encode(raw).decode(),'audio/ogg','queued',time.time(),chat['revision']))
        if chat['state']=='lia' and any(r['audio'] for r in rows):
            timer=threading.Timer(1.5,waiting_clip)
            timer.daemon=True
            timer.start()
        try:
            parts=[{'text':r['text'],'audio_base64':r['audio']} for r in rows]
            if chat['state'] != 'lia':
                for row in rows:
                    if row['audio']:
                        text=transcribe(row['audio'])
                        with db() as c:
                            c.execute('UPDATE messages SET text=? WHERE id=?',(text,row['id']))
                            record_message(c,c.execute('SELECT * FROM messages WHERE id=?',(row['id'],)).fetchone())
                out=None
            else:
                out=generate({'chat_id':body.chat,'message_id':body.id,'parts':parts,'reply_audio':any(r['audio'] for r in rows)})
                finished.set()
                transcripts=out.get('transcript','').split('\n\n')
                with db() as c:
                    for row in rows:
                        if row['audio'] and transcripts:
                            c.execute('UPDATE messages SET text=? WHERE id=?',(transcripts.pop(0),row['id']))
                            record_message(c,c.execute('SELECT * FROM messages WHERE id=?',(row['id'],)).fetchone())
            with db() as c:
                current=c.execute('SELECT * FROM chats WHERE id=?',(body.chat,)).fetchone()
                if out and current['state']=='lia' and current['revision']==chat['revision']:
                    escalation=out.get('handoff') or out.get('mode') in ['equipe','sem_fonte']
                    if escalation:
                        record_handoff(c,body.id,'Pedido de atendente' if out.get('handoff') else 'Avaliação da equipe')
                        out['text']='Vou encaminhar sua conversa para a equipe da EdUCA. Uma pessoa poderá ajudar você por aqui.'
                        c.execute("UPDATE chats SET state='waiting',reason=?,updated=? WHERE id=?", ('Solicitação de atendimento' if out.get('handoff') else 'Precisa de avaliação da equipe',time.time(),body.chat))
                    c.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?)', ('lia:'+body.id,body.chat,'lia',out['text'],out.get('audio_base64',''),out.get('audio_mime',''),'queued',time.time(),chat['revision']))
                c.execute("UPDATE batches SET status='done' WHERE id=?",(body.id,))
        except Exception as error:
            with db() as c:
                record_handoff(c,body.id,'Falha no processamento')
                c.execute("UPDATE batches SET status='error' WHERE id=?",(body.id,))
                c.execute("UPDATE chats SET state=CASE WHEN state='lia' THEN 'waiting' ELSE state END,revision=revision+1,reason=?,updated=? WHERE id=? AND revision=?", ('Falha ao preparar resposta: '+type(error).__name__,time.time(),body.chat,chat['revision']))
            raise HTTPException(503,'Conversa encaminhada à equipe após falha no processamento.')
        finally:
            finished.set()
            if timer: timer.cancel()
        return {'ok':True}

    @panel.post('/bridge/poll', dependencies=[Depends(bridge)])
    def poll():
        with db() as c:
            expire(c)
            c.execute('INSERT OR REPLACE INTO connection VALUES (1,?,?)',(time.time(),''))
            chats=[dict(r) for r in c.execute('SELECT * FROM chats')]
            queued=[dict(r) for r in c.execute("SELECT id,chat FROM messages WHERE status='queued' ORDER BY created LIMIT 20")]
        return {'chats':chats,'queued':queued}

    class Claim(BaseModel):
        id: str = Field(min_length=1,max_length=300)

    @panel.post('/bridge/claim', dependencies=[Depends(bridge)])
    def claim(body: Claim):
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT m.*,c.state,c.revision current_revision FROM messages m JOIN chats c ON c.id=m.chat WHERE m.id=?',(body.id,)).fetchone()
            if not row or row['status']!='queued': raise HTTPException(409,'Envio já reservado ou cancelado.')
            permitted=row['revision']==row['current_revision'] and ((row['role']=='lia' and row['state'] in ['lia','waiting']) or (row['role']=='human' and row['state']=='human'))
            if not permitted:
                c.execute("UPDATE messages SET status='cancelled' WHERE id=?",(body.id,))
                return {'cancelled':True}
            c.execute("UPDATE messages SET status='sending',created=? WHERE id=?",(time.time(),body.id))
            return {'id':row['id'],'chat':row['chat'],'text':row['text'],'audio_base64':row['audio'],'audio_mime':row['mime']}

    class Ack(Claim):
        ok: bool
        error: str = Field(default='',max_length=500)

    @panel.post('/bridge/ack', dependencies=[Depends(bridge)])
    def ack(body: Ack):
        with db() as c:
            row=c.execute("SELECT chat FROM messages WHERE id=? AND status='sending'",(body.id,)).fetchone()
            if row:
                c.execute('UPDATE messages SET status=? WHERE id=?',('sent' if body.ok else 'uncertain',body.id))
                if not body.ok: c.execute("UPDATE chats SET state='waiting',revision=revision+1,reason=?,updated=? WHERE id=?",('Envio incerto: '+body.error,time.time(),row['chat']))
        return {'ok':True}

    return panel
