"""Mistura ambiente sintético discreto apenas nos áudios de espera, sem downloads.

Use --source com uma pasta de cópias limpas dos waiting-XX.ogg. Nunca use a
pasta de destino como fonte, para não acumular ruído a cada execução.
"""
from pathlib import Path
import argparse
import hashlib
import json
import av
import numpy as np

ROOT = Path(__file__).resolve().parent


def band_noise(noise, rate, low, high):
    spectrum = np.fft.rfft(noise)
    frequencies = np.fft.rfftfreq(len(noise), 1 / rate)
    spectrum *= (frequencies >= low) & (frequencies <= high)
    return np.fft.irfft(spectrum, n=len(noise))


def decode(path, rate=24000):
    frames = []
    with av.open(str(path)) as source:
        resampler = av.AudioResampler(format='fltp', layout='mono', rate=rate)
        for frame in source.decode(audio=0):
            frames.extend(f.to_ndarray().reshape(-1) for f in resampler.resample(frame))
        frames.extend(f.to_ndarray().reshape(-1) for f in resampler.resample(None))
    return np.concatenate(frames)


def add_ambience(voice, rate, seed):
    rng = np.random.default_rng(seed)
    # Meio segundo final deixa perceber o ambiente sem alongar a espera.
    speech = np.pad(voice, (0, int(rate * .5)))
    background = np.zeros_like(speech)
    position = .12
    while position < len(speech) / rate - .12:
        duration = rng.uniform(.025, .065)
        t = np.arange(int(rate * duration)) / rate
        attack = np.minimum(t / .0015, 1)
        envelope = attack * np.exp(-t / rng.uniform(.007, .015))
        noise = band_noise(rng.normal(size=len(t)), rate, 650, 4500)
        click = envelope * (.65 * noise + .2 * np.sin(2 * np.pi * rng.uniform(900, 1800) * t)
                            + .15 * np.sin(2 * np.pi * rng.uniform(160, 280) * t))
        click *= rng.uniform(.012, .026) / max(np.max(np.abs(click)), 1e-8)
        start = int(position * rate)
        end = min(len(background), start + len(click))
        background[start:end] += click[:end-start]
        position += rng.uniform(.085, .23)
        if rng.random() < .23:
            position += rng.uniform(.2, .45)
    # Ambiente muito baixo, sem vozes, música ou sons externos.
    room = band_noise(rng.normal(size=len(speech)), rate, 80, 600)
    room *= .00025 / max(np.sqrt(np.mean(room ** 2)), 1e-8)
    background += room
    window = np.ones(int(rate * .06)) / int(rate * .06)
    envelope = np.sqrt(np.maximum(np.convolve(speech ** 2, window, mode='same'), 0))
    duck = 1 - .65 * np.clip(envelope / .015, 0, 1)
    background *= duck
    voice_rms = np.sqrt(np.mean(voice ** 2))
    noise_rms = np.sqrt(np.mean(background ** 2))
    background *= min(1, voice_rms * 10 ** (-24 / 20) / max(noise_rms, 1e-8))
    fade = min(int(rate * .1), len(background) // 2)
    background[:fade] *= np.linspace(0, 1, fade)
    background[-fade:] *= np.linspace(1, 0, fade)
    mixed = speech + background
    mixed *= min(1, .94 / max(np.max(np.abs(mixed)), 1e-8))
    return mixed.astype(np.float32)


def encode(path, audio, rate=24000):
    with av.open(str(path), 'w', format='ogg') as output:
        stream = output.add_stream('libopus', rate=48000)
        stream.layout = 'mono'
        stream.bit_rate = 48000
        resampler = av.AudioResampler(format='s16', layout='mono', rate=48000)
        for start in range(0, len(audio), 4096):
            frame = av.AudioFrame.from_ndarray(audio[start:start+4096][None, :], format='fltp', layout='mono')
            frame.sample_rate = rate
            for converted in resampler.resample(frame):
                for packet in stream.encode(converted):
                    output.mux(packet)
        for converted in resampler.resample(None):
            for packet in stream.encode(converted):
                output.mux(packet)
        for packet in stream.encode(None):
            output.mux(packet)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    target = ROOT / 'assets/waiting'
    if args.source.resolve() == target.resolve():
        parser.error('A fonte precisa conter as gravações limpas, fora do destino.')
    manifest_path = target / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for i, entry in enumerate(manifest):
        voice = decode(args.source / entry['file'])
        mixed = add_ambience(voice, 24000, 420 + i)
        encode(target / entry['file'], mixed)
        entry['sha256'] = hashlib.sha256((target / entry['file']).read_bytes()).hexdigest()
        entry['ambience'] = 'synthetic-keyboard-v1'
        print(entry['file'], round(len(mixed) / 24000, 2), 'seconds')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
