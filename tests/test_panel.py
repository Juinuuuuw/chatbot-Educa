"""Fila, autenticação e intervenção humana sem enviar mensagens ao WhatsApp."""
import base64
import pathlib
import sqlite3
import sys
import tempfile
import threading
import time
import json
import unittest
from fastapi.testclient import TestClient
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from panel import create_panel

class PanelTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name)
        (self.root/'data').mkdir()
        self.output={'text':'Sim, são gratuitos.','handoff':False,'mode':'faq','transcript':''}
        self.generated=[]
        def generate(body):
            self.generated.append(body)
            return dict(self.output)
        self.generate=generate
        self.client=TestClient(create_panel(self.root,'private-test-token',lambda b:self.generate(b),lambda b:'Áudio transcrito'))
        self.addCleanup(self.client.close)
        self.headers={'X-Educa-Token':'private-test-token'}
        ticket=self.post('/bridge/ticket',{},bridge=True).json()['ticket']
        self.assertEqual(self.post('/session',{'ticket':ticket}).status_code,200)
        self.chat='contact@c.us'
        self.post('/bridge/register',{'chat':self.chat,'label':'Contato'},bridge=True)

    def post(self,path,body,bridge=False):
        return self.client.post(path,json=body,headers=self.headers if bridge else {})

    def snapshot(self):return self.client.get('/api/snapshot').json()
    def incoming(self,id='incoming-1',**extra):
        return self.post('/bridge/incoming',{'chat':self.chat,'id':id,'text':'São gratuitos?',**extra},bridge=True)
    def batch(self,id='batch-1',ids=None):
        return self.post('/bridge/batch',{'chat':self.chat,'id':id,'ids':ids or ['incoming-1']},bridge=True)

    def test_auth_ticket_one_use_and_origin(self):
        with TestClient(create_panel(self.root,'other-token',lambda b:{},lambda b:'')) as stranger:
            self.assertEqual(stranger.get('/api/snapshot').status_code,401)
        self.assertEqual(self.client.post('/bridge/poll',json={}).status_code,401)
        ticket=self.post('/bridge/ticket',{},True).json()['ticket']
        self.assertEqual(self.client.post('/session',json={'ticket':ticket},headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.post('/session',{'ticket':ticket}).status_code,200)
        self.assertEqual(self.post('/session',{'ticket':ticket}).status_code,401)

    def test_batch_and_delivery_are_idempotent(self):
        self.incoming();self.incoming()
        self.assertEqual(self.batch().status_code,200)
        self.assertEqual(self.batch().json()['duplicate'],True)
        self.assertEqual(len(self.generated),1)
        queued=self.post('/bridge/poll',{},True).json()['queued']
        self.assertEqual(len(queued),1)
        claim=self.post('/bridge/claim',{'id':queued[0]['id']},True)
        self.assertEqual(claim.status_code,200)
        self.assertEqual(self.post('/bridge/claim',{'id':queued[0]['id']},True).status_code,409)
        self.post('/bridge/ack',{'id':queued[0]['id'],'ok':True},True)
        self.assertEqual(self.post('/bridge/poll',{},True).json()['queued'],[])

    def test_take_cancels_queued_bot_and_requires_take_to_reply(self):
        self.incoming();self.batch()
        self.assertEqual(self.post('/api/reply',{'chat':self.chat,'text':'Olá'}).status_code,409)
        self.post('/api/action',{'chat':self.chat,'action':'take'})
        self.assertEqual(self.post('/bridge/poll',{},True).json()['queued'],[])
        self.assertEqual(self.post('/api/reply',{'chat':self.chat,'text':'Olá'}).status_code,200)
        self.assertEqual(self.snapshot()['chats'][0]['state'],'human')

    def test_take_during_generation_discards_answer(self):
        started=threading.Event();finish=threading.Event()
        def slow(body):
            started.set();finish.wait(5);return self.output
        self.generate=slow
        self.incoming()
        worker=threading.Thread(target=self.batch)
        worker.start();self.assertTrue(started.wait(3))
        self.post('/api/action',{'chat':self.chat,'action':'take'})
        finish.set();worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(self.post('/bridge/poll',{},True).json()['queued'],[])

    def test_handoff_and_restricted_go_to_queue(self):
        for mode,handoff in [('regra',True),('equipe',False),('sem_fonte',False)]:
            self.output.update(mode=mode,handoff=handoff)
            self.post('/api/action',{'chat':self.chat,'action':'return'})
            self.incoming('m-'+mode)
            self.batch('b-'+mode,['m-'+mode])
            self.assertEqual(self.snapshot()['chats'][0]['state'],'waiting')

    def test_human_audio_transcribed_without_llm_and_recording_queued(self):
        self.post('/api/action',{'chat':self.chat,'action':'take'})
        audio=base64.b64encode(b'fake test audio').decode()
        self.incoming(audio_base64=audio,text='')
        self.batch()
        self.assertEqual(self.generated,[])
        rows=self.client.get('/api/messages',params={'chat':self.chat}).json()
        self.assertEqual(rows[0]['text'],'Áudio transcrito')
        reply=self.post('/api/reply',{'chat':self.chat,'audio_base64':audio,'audio_mime':'audio/webm'})
        self.assertEqual(reply.status_code,200)
        self.assertEqual(self.client.get('/api/audio',params={'id':reply.json()['id']}).content,b'fake test audio')

    def test_uncertain_send_is_not_retried(self):
        self.post('/api/action',{'chat':self.chat,'action':'take'})
        id=self.post('/api/reply',{'chat':self.chat,'text':'Olá'}).json()['id']
        self.post('/bridge/claim',{'id':id},True)
        self.post('/bridge/ack',{'id':id,'ok':False,'error':'Conexão perdida'},True)
        self.assertEqual(self.snapshot()['chats'][0]['state'],'waiting')
        self.assertEqual(self.post('/bridge/poll',{},True).json()['queued'],[])

    def test_operator_message_pauses_lia_and_group_not_registered(self):
        self.assertEqual(self.post('/bridge/register',{'chat':'group@g.us','label':'Grupo'},True).status_code,422)
        self.incoming(from_me=True)
        self.assertEqual(self.snapshot()['chats'][0]['state'],'human')

    def test_waiting_clip_is_queued_while_audio_generation_runs(self):
        folder=self.root/'assets/waiting'
        folder.mkdir(parents=True)
        (folder/'waiting-01.ogg').write_bytes(b'fake waiting audio')
        (folder/'manifest.json').write_text(json.dumps([{'id':'wait-01','file':'waiting-01.ogg','text':'Um momento'}]))
        started=threading.Event();finish=threading.Event()
        def slow(body):
            started.set();finish.wait(5);return {**self.output,'transcript':'Olá'}
        self.generate=slow
        self.incoming(text='',audio_base64=base64.b64encode(b'fake audio').decode())
        worker=threading.Thread(target=self.batch)
        worker.start();self.assertTrue(started.wait(3))
        try:
            time.sleep(1.7)
            queued=self.post('/bridge/poll',{},True).json()['queued']
            self.assertEqual(len(queued),1)
            self.assertTrue(queued[0]['id'].startswith('wait:'))
            self.post('/api/action',{'chat':self.chat,'action':'take'})
        finally:
            finish.set();worker.join(5)
        self.assertEqual(self.post('/bridge/poll',{},True).json()['queued'],[])

if __name__=='__main__':unittest.main()
