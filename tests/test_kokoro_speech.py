import pathlib
import sys
import unittest
import numpy as np
from unittest.mock import Mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from kokoro_speech import speech_pieces, synthesize
from build_waiting_ambience import add_ambience


class KokoroSpeechTest(unittest.TestCase):
    def test_long_answer_preserves_all_words_and_punctuation(self):
        text = 'Boa noite! ' + ' '.join(['Você pode consultar os dias e horários das aulas.'] * 18)
        pieces = speech_pieces(text)
        self.assertEqual(' '.join(pieces), text)
        self.assertTrue(all(len(piece) <= 240 for piece in pieces))
        self.assertTrue(pieces[0].startswith('Boa noite! Você'))

    def test_pause_between_ideas_and_question_punctuation_preserved(self):
        first = 'Você quer saber quais são os dias e horários das aulas de teatro?'
        second = 'Posso ajudar você.'
        voice = Mock()
        voice.create.return_value = (np.ones(100, dtype=np.float32) * .1, 24000)
        audio, rate = synthesize(voice, first + ' ' + second)
        self.assertEqual(voice.create.call_args_list[0].args[0], first)
        self.assertEqual(len(audio), 200 + int(rate * .3))
        self.assertTrue((audio[100:-100] == 0).all())
        self.assertEqual(voice.create.call_args.kwargs['speed'], .96)

    def test_invalid_generation_is_not_sent(self):
        voice = Mock()
        voice.create.return_value = (np.zeros(100), 24000)
        with self.assertRaisesRegex(RuntimeError, 'silencioso'):
            synthesize(voice, 'Boa noite!')

    def test_keyboard_stays_quiet_and_no_clipping(self):
        rate = 24000
        t = np.arange(rate * 2) / rate
        voice = (.1 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
        mixed = add_ambience(voice, rate, 42)
        delta = mixed - np.pad(voice, (0, len(mixed)-len(voice)))
        ratio = np.sqrt(np.mean(delta ** 2)) / np.sqrt(np.mean(voice ** 2))
        self.assertLessEqual(ratio, 10 ** (-24 / 20))
        self.assertLess(np.max(np.abs(mixed)), .95)
        self.assertGreater(np.max(np.abs(delta)), 0)


if __name__ == '__main__':
    unittest.main()
