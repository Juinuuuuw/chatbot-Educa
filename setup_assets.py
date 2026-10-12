import pathlib, json, requests, tarfile, io, hashlib, shutil
from huggingface_hub import snapshot_download
ROOT=pathlib.Path(__file__).resolve().parent
MODELS=ROOT/'models'; MODELS.mkdir(exist_ok=True)
EXT=ROOT/'extension'; EXT.mkdir(exist_ok=True)
def download(url,path):
    if path.exists(): return
    r=requests.get(url,timeout=120); r.raise_for_status(); path.write_bytes(r.content)
base='https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/'
for f in ['pt_BR-faber-medium.onnx','pt_BR-faber-medium.onnx.json','MODEL_CARD']:
    download(base+f,MODELS/f)
print('Voz baixada',flush=True)
kokoro_dir=MODELS/'kokoro'; kokoro_dir.mkdir(exist_ok=True)
kokoro_base='https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/'
for filename in ['kokoro-v1.0.onnx','voices-v1.0.bin']:
    download(kokoro_base+filename,kokoro_dir/filename)
print('Voz Kokoro baixada',flush=True)
snapshot_download('supertone-oss-archive/supertonic-3',revision='aafc6e32416a594460b32413efc49d7fe4ce6d46',local_dir=str(MODELS/'supertonic-3'),allow_patterns=['onnx/*','voice_styles/*','LICENSE','README.md'])
print('Vozes femininas Supertonic baixadas',flush=True)
snapshot_download('Systran/faster-whisper-small',local_dir=str(MODELS/'whisper-small'),allow_patterns=['model.bin','config.json','tokenizer.json','vocabulary.*'])
print('Transcrição baixada',flush=True)
meta=requests.get('https://registry.npmjs.org/@wppconnect/wa-js/4.6.1',timeout=30).json()
r=requests.get(meta['dist']['tarball'],timeout=60); r.raise_for_status()
actual=base64_digest=__import__('base64').b64encode(hashlib.sha512(r.content).digest()).decode()
if meta['dist'].get('integrity') != 'sha512-'+actual: raise ValueError('Integridade do WA-JS inválida')
with tarfile.open(fileobj=io.BytesIO(r.content),mode='r:gz') as tf:
    for name in ['package/dist/wppconnect-wa.js','package/LICENSE']:
        item=tf.extractfile(name)
        (EXT/('wppconnect-wa.js' if name.endswith('.js') else 'LICENSE-WA-JS')).write_bytes(item.read())
(EXT/'vendor.json').write_text(json.dumps({'package':'@wppconnect/wa-js','version':'4.6.1','integrity':meta['dist']['integrity']},indent=2))
print('Biblioteca da extensão verificada',flush=True)
