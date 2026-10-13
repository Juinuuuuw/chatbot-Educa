import io
import json
import pathlib
import sys
import unittest
import wave
import tempfile
import os
import time
import base64
from unittest.mock import patch, Mock

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import server

class ChatterboxIntegrationTest(unittest.TestCase):
    def test_local_process_receives_normalized_text_after_gpu_release(self):
        events=[]
        def unload(*args,**kwargs):
            events.append('unload');return Mock()
        def generate(command,**kwargs):
            events.append('voice')
            params=json.loads(kwargs['input'])
            self.assertIn('educa',params['text'])
            self.assertEqual(params['device'],'cuda')
            self.assertNotIn('token',params)
            with wave.open(command[-1],'wb') as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000)
                wav.writeframes(b'\x01\x00'*240)
            return Mock(returncode=0)
        with patch.dict(server.config,{'tts_engine':'chatterbox','chatterbox_python':sys.executable,'chatterbox_device':'cuda'}), patch.object(server.requests,'post',side_effect=unload) as request, patch.object(server,'run_voice_process',side_effect=generate):
            output=server.synthesize_wav('Oi, sou a Lia da EdUCA!')
            self.assertTrue(output.startswith(b'RIFF'))
            self.assertEqual(events,['unload','voice'])
            self.assertEqual(request.call_args.kwargs['json']['keep_alive'],0)

    def test_missing_environment_is_reported_without_using_cloud_voice(self):
        with patch.dict(server.config,{'tts_engine':'chatterbox','chatterbox_python':str(server.ROOT/'missing-env/python.exe')}), patch.object(server.requests,'post') as request:
            with self.assertRaisesRegex(RuntimeError,'Ambiente Chatterbox ausente'):
                server.synthesize_wav('Oi')
            request.assert_not_called()

    def test_same_answer_reuses_audio_and_expired_audio_is_regenerated(self):
        buffer=io.BytesIO()
        with wave.open(buffer,'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000)
            wav.writeframes(b'\x01\x00'*2400)
        with tempfile.TemporaryDirectory() as folder, patch.object(server,'VOICE_CACHE',pathlib.Path(folder)), patch.dict(server.config,{'tts_engine':'chatterbox'}), patch.object(server,'synthesize_wav',return_value=buffer.getvalue()) as synthesize:
            first=server.speak('Olá!')
            self.assertEqual(server.speak('Olá!'),first)
            synthesize.assert_called_once()
            cached=next(pathlib.Path(folder).glob('*.ogg'))
            os.utime(cached,(time.time()-86401,time.time()-86401))
            self.assertTrue(base64.b64decode(server.speak('Olá!')).startswith(b'OggS'))
            self.assertEqual(synthesize.call_count,2)

    def test_timeout_stops_voice_process_tree(self):
        proc=Mock(pid=987654)
        proc.communicate.side_effect=[server.subprocess.TimeoutExpired('voz',300),('','')]
        with patch.object(server.subprocess,'Popen',return_value=proc), patch.object(server.subprocess,'run') as kill:
            with self.assertRaisesRegex(RuntimeError,'tempo limite'):
                server.run_voice_process(['python','voz.py'],input='{}',timeout=300)
            if os.name=='nt':kill.assert_called_once_with(['taskkill','/PID','987654','/T','/F'],stdout=server.subprocess.DEVNULL,stderr=server.subprocess.DEVNULL)
            else:proc.kill.assert_called_once()

    def test_waiting_audio_is_prerecorded_and_available_while_processing(self):
        with patch.object(server,'synthesize_wav') as synthesize:
            with server.lock:
                first=server.waiting_audio()
                second=server.waiting_audio(exclude=first['id'])
            self.assertNotEqual(first['id'],second['id'])
            self.assertTrue(base64.b64decode(first['audio_base64']).startswith(b'OggS'))
            self.assertEqual(first['audio_mime'],'audio/ogg')
            synthesize.assert_not_called()

if __name__=='__main__':unittest.main()
