"""Instala a voz PT-BR local em ambiente separado; não altera o ambiente da API."""
from pathlib import Path
import json
import subprocess
import sys
import requests
from huggingface_hub import hf_hub_download

ROOT=Path(__file__).resolve().parent
MODELS=ROOT/'models/chatterbox-pt-br'
REVISIONS=json.loads((ROOT/'vendor/chatterbox/SOURCES.json').read_text())
REFERENCE='https://storage.googleapis.com/chatterbox-demo-samples/mtl-v3-single-language-prompts/pt-br/pt_br_f2.wav'

def main():
    environment=ROOT/'.venv-chatterbox'
    subprocess.run([sys.executable,'-m','venv',str(environment)],check=True)
    python=environment/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
    subprocess.run([str(python),'-m','pip','install','--no-cache-dir','torch==2.6.0','torchaudio==2.6.0','--index-url','https://download.pytorch.org/whl/cu124'],check=True)
    subprocess.run([str(python),'-m','pip','install','--no-cache-dir','-r',str(ROOT/'requirements-chatterbox.txt')],check=True)
    MODELS.mkdir(parents=True,exist_ok=True)
    files={'ResembleAI/Chatterbox-Multilingual-pt-br':['t3_pt_br.safetensors','s3gen_v3.pt','grapheme_mtl_merged_expanded_v1.json','README.md'],
           'ResembleAI/chatterbox':['ve.pt','conds.pt']}
    for repo,names in files.items():
        for name in names:
            hf_hub_download(repo,name,revision=REVISIONS[repo],local_dir=str(MODELS))
    response=requests.get(REFERENCE,timeout=60);response.raise_for_status()
    (MODELS/'reference-female.wav').write_bytes(response.content)
    (MODELS/'LICENSE').write_bytes((ROOT/'vendor/chatterbox/LICENSE').read_bytes())
    path=ROOT/'local.json'
    if not path.exists():
        from configurar import main as configure
        configure()
    config=json.loads(path.read_text(encoding='utf-8'))
    config.update(tts_engine='chatterbox',tts_voice='pt-br-female',chatterbox_python=str(python),
                  chatterbox_device='cuda',chatterbox_exaggeration=0.5,chatterbox_cfg_weight=0.35)
    path.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Voz local configurada. Reinicie a API depois de verificar uma amostra.')

if __name__=='__main__':main()
