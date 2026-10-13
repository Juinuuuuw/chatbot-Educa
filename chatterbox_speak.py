"""Gera WAV com o Chatterbox PT-BR local em um processo que libera a GPU ao sair."""
from pathlib import Path
import argparse
import json
import os
import sys
import time
from contextlib import nullcontext

ROOT=Path(__file__).resolve().parent
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
sys.path.insert(0,str(ROOT/'vendor'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--models',type=Path,default=ROOT/'models/chatterbox-pt-br')
    args=parser.parse_args()
    settings=json.load(sys.stdin)
    import torch
    import soundfile as sf
    from chatterbox.tts import ChatterboxTTS
    torch.set_num_threads(4)
    torch.manual_seed(42)
    device=settings.get('device','cuda' if torch.cuda.is_available() else 'cpu')
    started=time.monotonic()
    model=ChatterboxTTS.from_local(args.models,device)
    if device=='cuda': model.t3.half()
    loaded=time.monotonic()
    print('Chatterbox PT-BR carregado em '+device,file=sys.stderr,flush=True)
    reference=args.models/'reference-female.wav'
    # Fragmentos curtos preservam o texto inteiro e evitam corte pelo limite de tokens.
    import re
    sentences=re.split(r'(?<=[.!?])\s+',settings['text'])
    pieces=[];buffer=''
    for sentence in sentences:
        words=sentence.split()
        for word in words:
            if len(buffer)+len(word)>240:
                pieces.append(buffer.strip());buffer=''
            buffer+=word+' '
    if buffer.strip():pieces.append(buffer.strip())
    audio=[]
    for piece in pieces:
        with torch.autocast('cuda',dtype=torch.float16) if device=='cuda' else nullcontext():
            wav=model.generate(piece,language_id='pt',audio_prompt_path=str(reference),
                               exaggeration=settings.get('exaggeration',0.5),
                               cfg_weight=settings.get('cfg_weight',0.35),temperature=0.65)
        audio.append(wav.squeeze(0).float().cpu().numpy())
    import numpy as np
    if not audio: raise ValueError('Texto vazio para síntese.')
    pause=np.zeros(int(model.sr*0.16),dtype=np.float32)
    joined=np.concatenate([part for i,wav in enumerate(audio) for part in ([pause,wav] if i else [wav])])
    if not np.isfinite(joined).all() or np.max(np.abs(joined))<1e-5:
        raise RuntimeError('O modelo gerou áudio inválido ou silencioso.')
    sf.write(str(args.output),joined,model.sr,subtype='PCM_16')
    print(json.dumps({'device':device,'load_seconds':round(loaded-started,2),
                      'generation_seconds':round(time.monotonic()-loaded,2),
                      'audio_seconds':round(len(joined)/model.sr,2),
                      'gpu_peak_mb':round(torch.cuda.max_memory_allocated()/1024**2) if device=='cuda' else 0}))

if __name__=='__main__':main()
