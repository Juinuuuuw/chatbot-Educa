"""Fraseado local do Kokoro: preserva a pontuação e respira entre ideias."""
import re


def speech_pieces(text, limit=240):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    pieces = []
    pending = ''
    for sentence in sentences:
        for word in sentence.split():
            if pending and len(pending) + len(word) + 1 > limit:
                pieces.append(pending)
                pending = ''
            pending = (pending + ' ' + word).strip()
        # Saudações curtas ficam com a frase seguinte, evitando voz fragmentada.
        if len(pending) >= 60:
            pieces.append(pending)
            pending = ''
    if pending:
        pieces.append(pending)
    return pieces


def synthesize(kokoro, text, voice='pf_dora', speed=.96, sentence_pause=.3, clause_pause=.14):
    import numpy as np
    parts = speech_pieces(text)
    if not parts:
        raise ValueError('Texto vazio para síntese.')
    audio = []
    rate = None
    for i, piece in enumerate(parts):
        samples, current_rate = kokoro.create(piece, voice=voice, speed=speed,
            lang='pt-br', sentence_pause=sentence_pause, clause_pause=clause_pause)
        if rate is not None and current_rate != rate:
            raise RuntimeError('Taxa de áudio inconsistente.')
        rate = current_rate
        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        if not len(samples) or not np.isfinite(samples).all() or np.max(np.abs(samples)) < 1e-5:
            raise RuntimeError('O Kokoro gerou áudio inválido ou silencioso.')
        if i:
            ending = parts[i-1][-1:]
            pause = sentence_pause if ending in '.!?' else clause_pause
            audio.append(np.zeros(int(rate * pause), dtype=np.float32))
        audio.append(samples)
    return np.concatenate(audio), rate
