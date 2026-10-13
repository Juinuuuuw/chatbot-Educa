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
    parser.add_argument('--output',type=Path)
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
    reference=ROOT/'assets/lia-reference.wav'
    if not reference.exists(): reference=args.models/'reference-female.wav'
    model.prepare_conditionals(str(reference),exaggeration=settings.get('exaggeration',0.55))
    items=settings.get('items') or [{'text':settings['text'],'output':str(args.output)}]
    for item in items:
        if not item.get('output') or item['output']=='None': raise ValueError('Arquivo de saída ausente.')
        generate_item(model,item,settings,device)
    print(json.dumps({'device':device,'load_seconds':round(loaded-started,2),
                      'generation_seconds':round(time.monotonic()-loaded,2),
                      'gpu_peak_mb':round(torch.cuda.max_memory_allocated()/1024**2) if device=='cuda' else 0}))

def generate_item(model,item,settings,device):
    import torch
    import soundfile as sf
    # Fragmentos curtos preservam o texto inteiro e evitam corte pelo limite de tokens.
    import re
    sentences=re.split(r'(?<=[.!?])\s+',item['text'])
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
            wav=model.generate(piece,language_id='pt',
                               exaggeration=settings.get('exaggeration',0.55),
                               cfg_weight=settings.get('cfg_weight',0.5),temperature=0.65)
        audio.append(wav.squeeze(0).float().cpu().numpy())
    import numpy as np
    if not audio: raise ValueError('Texto vazio para síntese.')
    pause=np.zeros(int(model.sr*0.16),dtype=np.float32)
    joined=np.concatenate([part for i,wav in enumerate(audio) for part in ([pause,wav] if i else [wav])])
    if not np.isfinite(joined).all() or np.max(np.abs(joined))<1e-5:
        raise RuntimeError('O modelo gerou áudio inválido ou silencioso.')
    # Leve ajuste de presença, corte de graves e nível consistente para voz no WhatsApp.
    from scipy.signal import butter,sosfilt,lfilter
    joined=sosfilt(butter(2,80,fs=model.sr,btype='highpass',output='sos'),joined)
    frequency=2200;gain=2.5;q=0.8
    a=10**(gain/40);omega=2*np.pi*frequency/model.sr;alpha=np.sin(omega)/(2*q)
    b=np.array([1+alpha*a,-2*np.cos(omega),1-alpha*a])
    d=np.array([1+alpha/a,-2*np.cos(omega),1-alpha/a])
    joined=lfilter(b/d[0],d/d[0],joined)
    rms=float(np.sqrt(np.mean(joined**2)));peak=float(np.max(np.abs(joined)))
    joined*=min(10**(-20/20)/max(rms,1e-8),0.94/max(peak,1e-8))
    Path(item['output']).parent.mkdir(parents=True,exist_ok=True)
    sf.write(item['output'],joined,model.sr,subtype='PCM_16')
    print(json.dumps({'file':Path(item['output']).name,'audio_seconds':round(len(joined)/model.sr,2)}),flush=True)

if __name__=='__main__':main()
