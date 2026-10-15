"""Reconhece a API existente antes de tentar abrir outra na mesma porta."""
import json
import pathlib
import socket
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent

def main():
    config_path = ROOT / 'local.json'
    config = {}
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding='utf-8'))
        req = urllib.request.Request(
            'http://127.0.0.1:'+str(config.get('port',8765))+'/health',
            headers={'X-Educa-Token': config['token']},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                status = json.load(response)
            if status.get('ok') and status.get('model') == config['model'] and 'chunks' in status:
                print('A API do Educa ja esta funcionando. Nao precisa abrir outra janela.')
                print('Pode conectar o atendimento pela extensao do navegador.')
                return 0
        except (OSError, ValueError):
            pass
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', config.get('port',8765)))
        except OSError:
            print(f"A porta {config.get('port',8765)} esta ocupada, mas a API do Educa nao respondeu corretamente.")
            print('Informe esta mensagem no chat para verificar o servico existente.')
            return 1
    from server import app
    import uvicorn
    print('Iniciando a API do Educa. Mantenha esta janela aberta.')
    uvicorn.run(app, host='127.0.0.1', port=config.get('port',8765), access_log=False, use_colors=False)
    return 0

if __name__ == '__main__':
    sys.exit(main())
