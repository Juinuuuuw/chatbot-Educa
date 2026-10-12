# Chatbot Educa

Protótipo de atendimento para a EdUCA/UERN Natal pelo WhatsApp Web. Combina regras para perguntas frequentes, recuperação lexical BM25 de documentos oficiais e Phi-4 Mini executada pelo Ollama. A extensão para Brave/Chromium responde a mensagens novas na conversa ativada pelo usuário.

## Tecnologias

- Python, FastAPI e Uvicorn: API local em `127.0.0.1:8765`.
- JavaScript, HTML e Manifest V3: extensão com WA-JS 4.6.1.
- Ollama e `phi4-mini:latest`: geração de respostas.
- BM25: recuperação do edital e de notícias; sem embeddings.
- faster-whisper small: transcrição local na CPU.
- edge-tts e voz Microsoft Francisca: síntese **online** do texto da resposta.
- SQLite: histórico curto e controle de repetição.

Não exige chave paga de LLM ou de síntese. A voz padrão depende de internet e envia o texto da resposta ao serviço Microsoft; a disponibilidade desse serviço pode mudar. A integração com WhatsApp Web é não oficial.

## Instalação no Windows

Instale Python 3.11 e Ollama. Em um terminal na pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull phi4-mini:latest
.\.venv\Scripts\python.exe configurar.py
.\.venv\Scripts\python.exe setup_assets.py
```

O último passo baixa os modelos locais de áudio e confere a integridade da biblioteca WA-JS. Os arquivos podem ocupar vários GB. Os modelos não são incluídos no Git. Há alternativas locais Piper, Kokoro e Supertonic no código; precisam dos respectivos modelos e devem ser avaliadas antes do atendimento.

`configurar.py` gera uma chave aleatória em `local.json` e grava a mesma chave em `extension/config.js`. Ambos são ignorados pelo Git. O script preserva configurações e chaves existentes; execute-o novamente após alterar a chave e recarregue a extensão.

### Extensão no Brave

1. Abra `brave://extensions` e habilite o modo do desenvolvedor.
2. Escolha **Carregar descompactada** e selecione a pasta `extension`.
3. Abra ou recarregue o WhatsApp Web.
4. Inicie a API com `INICIAR.cmd`, mantendo o Ollama disponível.
5. Abra **Mensagem para você**, marque a opção correspondente no painel da extensão e clique em **Ativar na conversa aberta**.
6. Envie uma pergunta normal ou grave um áudio curto. Não precisa usar tag.
7. Pause o atendimento ao terminar o teste.

Somente a conversa ativada é atendida. Para uma conversa individual com outra pessoa, desmarque a opção de teste. A extensão não atende grupos. Um pedido de atendente pausa o bot; não chama nem notifica uma pessoa automaticamente.

## Base de conhecimento

`data/` contém uma cópia do edital 019/2026, documentos extraídos, trechos e 20 registros de turmas conferidos na tabela. A base inicial tem 17 documentos (sete páginas do edital e dez notícias), 34 trechos e 20 registros de turmas. As fontes constam de `data/documents.json`.

A base é histórica e não confirma vagas ou inscrições atuais. Para atualizá-la, pare a API, execute a ingestão e reinicie:

```powershell
.\.venv\Scripts\python.exe ingest.py
# Para fornecer outro arquivo do edital:
.\.venv\Scripts\python.exe ingest.py --pdf "C:\pasta\uern-educa-0192026edital.pdf"
```

A ingestão atualiza os documentos e trechos. Os registros de turmas em `data/courses.json` são uma transcrição separada e precisam de revisão manual quando o edital mudar.

## Configuração e GPU

Edite `local.json` para escolher voz e modelo. O exemplo deixa o Ollama decidir automaticamente a distribuição entre CPU e GPU. Neste computador, uma GTX 1650 de 4 GB foi testada com `"ollama_num_gpu": 99` e contexto de 3072 tokens, carregando a Phi-4 Mini inteira na GPU. Essa opção depende da memória disponível; a transcrição permanece na CPU.

## Dados locais e limitações

O histórico tem até quatro pares de pergunta/resposta por conversa e retenção de até 24 horas. Seu conteúdo permanece legível no banco local. Áudios recebidos são processados em memória. Não publique `local.json`, `extension/config.js` ou o banco `data/runtime.sqlite3`.

Computador, API, Ollama e WhatsApp Web precisam estar disponíveis. Mudanças no WhatsApp podem quebrar a extensão ou causar restrição da conta. A validação dos componentes locais não garante funcionamento em qualquer sessão do navegador ou precisão da transcrição. Erros e envios incertos pausam o bot para evitar repetição.

## Documentação

- [Relatório técnico em PDF](docs/Chatbot_Educa_ABNT.pdf): arquitetura, seis diagramas, tecnologias e limites do protótipo.
- [Detalhes do comportamento](LEIA-ME.md): regras, personalidade e funcionamento do atendimento.
- `extension/LICENSE-WA-JS`: licença da biblioteca incluída. Os modelos baixados têm suas próprias licenças.

Este repositório não inclui credenciais, conversas pessoais, amostras de voz, ambiente Python ou pesos de modelos.
