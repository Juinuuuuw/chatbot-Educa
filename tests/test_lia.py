"""Casos de aceitação do atendimento, sem Ollama, serviço de voz ou WhatsApp."""
import base64
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import contextmanager, closing

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import server
from lia import TOPICS

@contextmanager
def temporary_db():
    with tempfile.TemporaryDirectory() as folder:
        path=pathlib.Path(folder)/'runtime.sqlite3'
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('CREATE TABLE responses (key TEXT PRIMARY KEY, response TEXT, created REAL)')
            db.execute('CREATE TABLE conversations (chat TEXT, message_key TEXT PRIMARY KEY, question TEXT, answer TEXT, created REAL)')
        with patch.object(server,'DB',path): yield path

class LiaTest(unittest.TestCase):
    def setUp(self):
        self.no_network = patch.object(server.requests, 'post', side_effect=AssertionError('Não deveria consultar o LLM'))
        self.no_network.start()
        self.addCleanup(self.no_network.stop)

    def test_text_greetings_show_menu(self):
        for q in ['Oi', 'Oii :)', 'Olá!', 'Bom dia', 'Boa tarde! Tudo bem?', 'Boa noite! Tudo bom?']:
            with self.subTest(q=q):
                result = server.answer(q)
                self.assertEqual(result['mode'], 'menu')
                self.assertIn('Sou a Lia', result['text'])
                self.assertIn('10. Novas turmas', result['text'])

    def test_audio_greeting_has_no_menu(self):
        result = server.answer('Boa noite! Tudo bom?', is_audio=True)
        self.assertEqual(result['mode'], 'saudacao_audio')
        self.assertIn('Boa noite!', result['text'])
        self.assertNotIn('1.', result['text'])

    def test_all_menu_options_are_static(self):
        for i in range(1, len(TOPICS)+1):
            result = server.answer(str(i))
            self.assertEqual(result['mode'], 'faq')
            self.assertNotIn('Posso ajudar com estas dúvidas', result['text'])

    def test_full_questions(self):
        questions = [
            'Quais cursos e atividades estão sendo oferecidos atualmente pela EdUCA?',
            'Como faço para me inscrever em um curso ou atividade da EdUCA?',
            'Quem pode participar das atividades?',
            'As atividades da EdUCA são gratuitas ou não?',
            'Quais são os dias e horários das aulas?',
            'Ainda há vagas disponíveis para determinado curso ou atividade?',
            'Onde acontecem as aulas e atividades da EdUCA?',
            'Quais documentos preciso apresentar para realizar a inscrição?',
            'Recebo certificado ao concluir o curso ou atividade?',
            'Como posso acompanhar a abertura de novas turmas, cursos e projetos da EdUCA?',
        ]
        for question in questions:
            with self.subTest(question=question):
                result = server.answer(question)
                self.assertEqual(result['mode'], 'faq')
                self.assertNotIn('1. Cursos', result['text'])

    def test_combined_static_questions(self):
        text = server.answer('Os cursos são gratuitos e quais documentos preciso levar?')['text']
        self.assertIn('gratuitos', text)
        self.assertIn('CPF', text)

    def test_current_offers_and_certificate_are_not_promised(self):
        self.assertIn('confirme com a equipe', server.answer('1')['text'])
        self.assertIn('Não consigo confirmar', server.answer('6')['text'])
        self.assertIn('Não encontrei', server.answer('9')['text'])

    def test_specific_schedule_and_followup(self):
        history = [{'question':'Tenho 60 anos, quero teatro', 'answer':'Teatro na Maturidade'}]
        text = server.answer('Quais os dias e horários das aulas?', history)['text']
        self.assertIn('17:30', text)
        self.assertIn('segunda', text)
        self.assertNotIn('50 anos', text)
        self.assertNotIn('vagas', text)

    def test_course_list_does_not_select_maturity_theater(self):
        history=[{'question':'1','answer':server.answer('1')['text']}]
        text=server.answer('Quais os dias e horários das aulas?',history)['text']
        self.assertIn('Qual curso',text)
        self.assertNotIn('17:30',text)

    def test_uncovered_question_is_forwarded_with_checked_facts(self):
        response=unittest.mock.Mock()
        response.json.return_value={'message':{'content':'Os cursos do edital são gratuitos. Não encontrei confirmação sobre experiência prévia; procure a equipe.'}}
        with patch.object(server.requests,'post',return_value=response) as call:
            result=server.answer('Os cursos são gratuitos? Preciso de experiência para teatro?')
            self.assertEqual(result['mode'],'rag_phi4')
            prompt=call.call_args.kwargs['json']['messages'][-1]['content']
            self.assertIn('experiência',prompt)
            self.assertIn('RESPOSTAS CONFERIDAS',prompt)

    def test_team_decisions_and_private_cases(self):
        for q in ['Pode abrir uma exceção para eu entrar na turma?', 'Consulte minha matrícula',
                  'Quero dados internos da EdUCA', 'Tenho uma lesão, posso fazer musculação?',
                  'Quero cancelar minha inscrição', 'Envie a lista de alunos', 'Preciso do meu certificado']:
            with self.subTest(q=q):
                result = server.answer(q)
                self.assertEqual(result['mode'], 'equipe')
                self.assertIn('Procure a equipe', result['text'])

    def test_unrelated_and_explicit_handoff(self):
        self.assertEqual(server.answer('Quem ganhou o jogo ontem?')['mode'], 'fora_escopo')
        self.assertTrue(server.answer('Quero um atendente')['handoff'])

    def test_audio_message_endpoint_returns_audio_without_menu(self):
        with tempfile.TemporaryDirectory() as folder:
            db_path = pathlib.Path(folder)/'runtime.sqlite3'
            with sqlite3.connect(db_path) as db:
                db.execute('CREATE TABLE responses (key TEXT PRIMARY KEY, response TEXT, created REAL)')
                db.execute('CREATE TABLE conversations (chat TEXT, message_key TEXT PRIMARY KEY, question TEXT, answer TEXT, created REAL)')
            db.close()
            with patch.object(server,'DB',db_path), patch.object(server,'transcribe',return_value='Oi'), patch.object(server,'speak',return_value='audio-falso') as speak:
                result = server.message(server.Message(chat_id='teste-local', message_id='audio-1',audio_base64=base64.b64encode(b'teste').decode()))
                self.assertEqual(result['mode'],'saudacao_audio')
                self.assertEqual(result['audio_mime'],'audio/ogg')
                self.assertEqual(result['audio_base64'],'audio-falso')
                self.assertNotIn('1. Cursos', result['text'])
                speak.assert_called_once()
                cached = server.message(server.Message(chat_id='teste-local',message_id='audio-1',audio_base64='teste'))
                self.assertEqual(cached,result)
                speak.assert_called_once()

    def test_text_sequence_returns_one_answer_to_all_questions(self):
        with temporary_db() as db_path:
            result=server.message(server.Message(chat_id='batch-text',message_id='batch-test-1',parts=[
                {'text':'Boa noite! Tudo bom?'},
                {'text':'Os cursos são gratuitos e quais documentos preciso levar?'},
                {'text':'Tenho 60 anos e quero fazer teatro. Posso participar?'},
            ]))
            self.assertTrue(result['text'].startswith('Boa noite!'))
            self.assertIn('gratuitos',result['text'])
            self.assertIn('CPF',result['text'])
            self.assertIn('Maturidade',result['text'])
            self.assertNotIn('1. Cursos',result['text'])
            with closing(sqlite3.connect(db_path)) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM conversations').fetchone()[0],1)

    def test_audio_sequence_transcribed_in_order_and_spoken_once(self):
        with temporary_db(), patch.object(server,'transcribe',side_effect=['Boa tarde','Os cursos são gratuitos?','Quais documentos preciso levar?']) as transcribe, patch.object(server,'speak',return_value='audio-unico') as speak:
            message=server.Message(chat_id='batch-audio',message_id='batch-test-2',parts=[
                {'audio_base64':'audio1'},{'audio_base64':'audio2'},{'audio_base64':'audio3'},
            ])
            result=server.message(message)
            self.assertEqual([call.args[0] for call in transcribe.call_args_list],['audio1','audio2','audio3'])
            self.assertEqual(result['audio_base64'],'audio-unico')
            self.assertIn('gratuitos',result['text'])
            self.assertIn('CPF',result['text'])
            self.assertNotIn('1. Cursos',result['text'])
            speak.assert_called_once()
            self.assertEqual(server.message(message),result)
            self.assertEqual(transcribe.call_count,3)
            speak.assert_called_once()

    def test_mixed_sequence_and_numeric_options(self):
        with temporary_db(), patch.object(server,'transcribe',return_value='Quais documentos preciso levar?'), patch.object(server,'speak',return_value='audio-unico'):
            result=server.message(server.Message(chat_id='batch-mixed',message_id='batch-test-3',parts=[
                {'text':'Oi'}, {'text':'4'}, {'audio_base64':'audio'},
            ]))
            self.assertIn('gratuitos',result['text'])
            self.assertIn('CPF',result['text'])
            self.assertEqual(result['audio_base64'],'audio-unico')
            self.assertNotIn('1. Cursos',result['text'])

    def test_unrecognized_audio_does_not_silently_drop_question(self):
        with temporary_db(), patch.object(server,'transcribe',return_value=''), patch.object(server,'speak') as speak:
            with self.assertRaises(server.HTTPException) as raised:
                server.message(server.Message(chat_id='batch-bad',message_id='batch-test-4',parts=[
                    {'text':'É gratuito?'},{'audio_base64':'inaudivel'},
                ]))
            self.assertEqual(raised.exception.status_code,422)
            self.assertIn('um dos áudios',raised.exception.detail)
            speak.assert_not_called()

    def test_voice_service_rejection_keeps_answer_and_cache(self):
        from aiohttp import WSServerHandshakeError
        failure=WSServerHandshakeError(request_info=None,history=(),status=403,message='Invalid response status')
        with temporary_db() as db_path, patch.dict(server.config,{'tts_engine':'edge'}), patch.object(server,'transcribe',return_value='Os cursos são gratuitos?') as transcribe, patch.object(server,'speak',side_effect=failure) as speak:
            m=server.Message(chat_id='voice-failure',message_id='voice-403',parts=[{'audio_base64':'audio-falso'}])
            result=server.message(m)
            self.assertIn('gratuitos',result['text'])
            self.assertIn('responder por texto',result['text'])
            self.assertIn('audio_warning',result)
            self.assertNotIn('audio_base64',result)
            self.assertEqual(result['audio_error']['http_status'],403)
            self.assertEqual(server.message(m),result)
            speak.assert_called_once();transcribe.assert_called_once()
            with closing(sqlite3.connect(db_path)) as db:
                history=db.execute('SELECT answer FROM conversations').fetchone()[0]
                self.assertIn('gratuitos',history)
                self.assertNotIn('responder por texto',history)

    def test_voice_timeout_falls_back_but_programming_error_does_not(self):
        with patch.dict(server.config,{'tts_engine':'edge'}), patch.object(server,'speak',side_effect=TimeoutError):
            out={'text':'Resposta pronta'}
            server.attach_audio(out)
            self.assertIn('audio_warning',out)
        with patch.dict(server.config,{'tts_engine':'edge'}), patch.object(server,'speak',side_effect=RuntimeError('Falha de conversão')):
            with self.assertRaises(RuntimeError): server.attach_audio({'text':'Resposta pronta'})

if __name__ == '__main__':
    unittest.main()
