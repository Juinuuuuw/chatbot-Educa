"""Cria a chave local e sincroniza a configuração da extensão sem publicá-la."""
import json
import pathlib
import secrets

ROOT = pathlib.Path(__file__).resolve().parent

def main():
    path = ROOT / 'local.json'
    if path.exists():
        config = json.loads(path.read_text(encoding='utf-8'))
    else:
        config = json.loads((ROOT / 'local.example.json').read_text(encoding='utf-8'))
    if not config.get('token'):
        config['token'] = secrets.token_urlsafe(32)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'extension' / 'config.js').write_text(
        'const EDUCA_TOKEN = ' + json.dumps(config['token']) + ';\n', encoding='utf-8'
    )
    print('Configuração local pronta. Recarregue a extensão se ela já estiver instalada.')

if __name__ == '__main__':
    main()
