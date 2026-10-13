# Lia — assistente virtual da EdUCA

Desde a versão 0.2.0, saudações simples por texto recebem um menu com dez dúvidas gerais e respostas estáticas. Perguntas completas são respondidas diretamente. Áudios recebem respostas faladas, sem menu. A Lia orienta a procura da equipe em questões individuais, decisões, informações internas e fatos sem confirmação oficial. Seu nome foi escolhido por ser curto, remeter a “ler” e soar muito bem em voz sintetizada.

API com regras, RAG por busca lexical BM25, Phi-4 Mini, transcrição local Whisper small e voz feminina local Chatterbox PT-BR. O RAG não usa embeddings e não foi treinado com conversas pessoais. A tabela do edital foi conferida visualmente e transcrita em 20 registros de turmas, totalizando 431 vagas originalmente previstas. Perguntas sobre turmas usam esses registros, para evitar mistura com notícias de anos anteriores.

## Personalidade e voz

Na versão 0.4.0, o perfil recebeu ajustes de referência, presença e volume. Há seis áudios de espera pré-gravados: um deles é enviado enquanto uma resposta falada mais lenta é preparada. Respostas rápidas não recebem aviso; o aviso não consome a pergunta e não se repete para a mesma sequência.

A voz padrão agora é Chatterbox PT-BR, gerada no computador com uma referência feminina sintética gerada anteriormente no protótipo. A API usa um ambiente separado para a voz e descarrega a Phi da GPU antes da síntese. Ao concluir, o processo de voz libera sua memória. Novas respostas podem levar cerca de um minuto nesta máquina; áudios de respostas iguais são reutilizados por até 24 horas, com limite de 128 arquivos em `data/voice-cache`. Consulte o README para instalação em outro computador.

As respostas usam um tom acolhedor, frases simples e, quando combinar com a conversa, um emoji discreto. Telefone e e-mail aparecem quando solicitados. As informações sobre prazos encerrados e a falta de confirmação de vagas atuais continuam sendo respeitadas. Esse tom vale para as regras e para o Phi-4 Mini.

O bot devolve a saudação recebida: “Bom dia”, “Boa tarde” ou “Boa noite”, inclusive quando ela acompanha uma pergunta. Antes da síntese, as grafias Educa, EdUCA e EDUCA são convertidas para `educa`, para evitar leitura como sigla. O texto mostrado no WhatsApp conserva a grafia original.

Para perguntas de participação no teatro com uma idade informada, as faixas Infantil, Juvenil, Adulto e Maturidade são conferidas diretamente na tabela. A resposta não acrescenta documentos, gratuidade ou horários. Quando há intenção de ingresso, informa que o item 10.3 do edital previa início das aulas em 3 de agosto de 2026 e que a base não confirma novas inscrições. Essa previsão não comprova início efetivo nem que aquela foi a última turma. A oferta de pausa para falar com a equipe continua sem notificá-la automaticamente.

Como alternativa opcional, `pt-BR-FranciscaNeural` é uma voz feminina do serviço online Microsoft Edge, acessado pela biblioteca comunitária `edge-tts`. Funciona no Brave e não exige instalar Edge, assinatura ou chave de API. A geração de voz precisa de internet e envia o texto preparado da resposta à Microsoft; a transcrição do áudio recebido e o Phi-4 continuam locais. Não é uma API oficial contratada e sua disponibilidade pode mudar. Desde a versão 0.3.1, falhas de conexão ou protocolo do serviço de voz fazem a Lia responder por texto com um aviso curto, preservando a resposta e mantendo o atendimento ativo. A voz selecionada não é alterada. Referência: https://github.com/rany2/edge-tts.

Para alterar a voz Microsoft, edite `tts_voice`, `tts_rate` ou `tts_pitch` em `local.json` e reinicie a API. O padrão é Francisca, velocidade `-3%` e tom `+2Hz`. Emojis não são pronunciados e horários são preparados para leitura. Não há controle explícito de sorriso. As alternativas locais podem ser baixadas com `setup_assets.py`: Supertonic (`tts_engine`: `supertonic`, `tts_voice`: `F2`, `tts_speed`: `1.0`), Kokoro (`tts_engine`: `kokoro`, `tts_voice`: `pf_dora`) ou Piper (`tts_engine`: `piper`). Supertonic usa OpenRAIL-M, preservada em `models/supertonic-3/LICENSE`; Kokoro usa Apache 2.0.

Perguntas combinadas sobre gratuidade, endereço, documentos ou adequação da idade ao Teatro na Maturidade acumulam as regras pertinentes. A idade mínima vem da tabela conferida do edital. Quando há horário ou outro assunto, os fatos dessas regras são enviados ao Phi-4 junto aos trechos recuperados para responder a todas as partes. Para teatro com idade de 50 anos ou mais, a busca prioriza Teatro na Maturidade. Isso confirma adequação à idade, não matrícula ou vagas atuais. Perguntas sobre teatro e dança deixam de usar notícias históricas para horários.

Dia e horário de uma turma identificada têm resposta direta com base na tabela, sem acrescentar idade ou vagas. O bot guarda até quatro pares de pergunta/resposta por conversa, separados por identificador criptograficamente resumido e por até 24 horas. Esse histórico começa nas novas mensagens após a atualização. Ele permite entender perguntas como “E qual o horário?”; as últimas duas trocas também contextualizam o Phi-4. Se a turma não foi identificada, o bot pede esclarecimento. Idade e disponibilidade aparecem quando solicitadas, sem rodapé obrigatório. A oferta de atendimento humano apenas pausa o bot; não notifica nem atribui a conversa a uma pessoa.

Neste computador, a GTX 1650 tem 4 GB de VRAM. O teste com `ollama_num_gpu: 99` e contexto de 3072 tokens carregou o Phi-4 Mini inteiro na GPU (`ollama ps`: 100% GPU), usando aproximadamente 2,9 GB na medição do driver. Uma comparação curta de geração mediu cerca de 20 tokens/s em modo misto e 41 tokens/s na GPU completa; não é garantia de latência para qualquer conversa. A configuração está em `local.json`; remover `ollama_num_gpu` devolve a decisão automática ao Ollama. Outros programas podem reduzir a memória disponível. A transcrição Whisper continua na CPU. O modelo permanece carregado por até cinco minutos após uma resposta com Phi-4.

## Instalar no Brave

1. Abra `brave://extensions`.
2. Ative **Modo do desenvolvedor**.
3. Clique em **Carregar sem compactação** (ou **Carregar descompactada**).
4. Escolha a pasta `extension` deste projeto, que contém `manifest.json`.
5. Recarregue a aba `https://web.whatsapp.com/`.
6. Abra a extensão pelo menu de extensões do Brave.

## Testar sem escrever para outra pessoa

Após uma atualização dos arquivos, abra `brave://extensions`, clique no botão de recarregar da extensão Educa e recarregue também o WhatsApp Web. A versão 0.1.1 remove o comando obrigatório e corrige a retomada após pausa e o filtro de mensagens no primeiro segundo da ativação. A opção de teste na própria conversa é lembrada ao reabrir o painel.

A versão 0.1.2 registra a identificação antes de enviar cada resposta, inclusive áudio, evitando a pausa quando o WhatsApp não devolve esse campo. Também identifica respostas do próprio bot por seu token, mesmo se o WhatsApp mudar a representação do contato. As novas respostas faladas usam OGG/Opus, e o painel informa a etapa atual do processamento.

1. A API precisa estar rodando. Para iniciá-la novamente, abra `INICIAR.cmd` e mantenha a janela aberta. Se a API já estiver funcionando, o iniciador informa isso e você pode fechar essa nova janela.
2. No WhatsApp, abra **Mensagem para você**.
3. Na extensão, marque **Testar em Mensagem para você** e clique **Ativar na conversa aberta**. Se estiver carregando, aguarde e tente novamente.
4. Envie normalmente `As inscrições estão abertas hoje?`. Não há comando ou tag obrigatória.
5. Envie `Qual o horário do teatro na maturidade e a idade mínima?` para testar o RAG com o Phi-4 Mini.
6. Grave um áudio curto perguntando se os cursos são gratuitos. O bot deve transcrever internamente e responder em áudio, sem seleção manual.
7. Clique **Pausar atendimento** ao terminar.

Para testar com outro telefone, abra uma conversa individual com esse contato, deixe a opção “Mensagem para você” desmarcada e ative. Somente mensagens novas recebidas nessa conversa serão respondidas. A extensão não atende automaticamente todas as conversas.

## Limitações

- Integração não oficial com o WhatsApp Web via WA-JS 4.6.1; mudanças da plataforma podem quebrá-la e existe risco de restrição da conta. A biblioteca está incluída localmente e sua integridade foi conferida.
- A instalação e o envio real no Brave precisam de validação pelo usuário; os testes locais não comprovam compatibilidade com a sessão atual do WhatsApp.
- Computador, API e WhatsApp Web precisam permanecer ligados. Mensagens são verificadas aproximadamente a cada cinco segundos com a aba ativa; o navegador pode atrasar isso em segundo plano.
- Uma mensagem é processada por vez. O Phi-4 Mini usa a configuração de GPU descrita acima; não há garantia de resposta instantânea. O contexto está limitado a 3072 tokens.
- Áudios de até 3 minutos e 12 MB; sotaques, ruído e nomes próprios precisam de avaliação com áudios reais. A síntese é voz artificial e não imita membros da equipe.
- Nos testes locais, a amostra sintética permitiu reconhecer a intenção de perguntar sobre gratuidade, mas a transcrição apresentou erros em números e nomes. Os testes comprovam funcionamento dos componentes, não precisão suficiente para atendimento institucional. Números e nomes devem ser confirmados pela equipe no piloto.
- O edital 019/2026 é histórico: os prazos de matrícula de julho de 2026 já passaram. O bot não consulta vagas em tempo real, não efetua matrícula e não recebe documentos.
- A base cobre o PDF fornecido e dez artigos do portal; não cobre todo o histórico da tag. Consulte `data/ingestion.json` para a lista de falhas e escopo.
- Erros pausam o atendimento. Um envio com resultado incerto não é repetido automaticamente.
- Pedido de atendente pausa o bot; não notifica a equipe automaticamente. O contato é informado quando solicitado.
- Respostas, transcrições, áudio gerado e histórico curto de perguntas/respostas são guardados localmente por até 24 horas, com limpeza no início e ao processar mensagens. O histórico contém até quatro trocas por conversa. Os áudios recebidos são processados em memória. Identificadores processados ficam no armazenamento local da extensão, limitados aos últimos 2000.
- `local.json` e `extension/config.js` contêm a chave de acesso local. Não compartilhe esses arquivos ou a pasta sem trocar essa chave. A API escuta apenas em `127.0.0.1:8765` e exige autenticação.

## Arquivos

- `server.py`: API e regras.
- `ingest.py`: extração do PDF e artigos oficiais; execute com a API parada para atualizar a base e reinicie depois.
- `data/documents.json`: documentos com origem, data e página.
- `data/chunks.json`: trechos usados para recuperação.
- `models/`: modelos locais de transcrição e voz.
- `extension/`: extensão pronta para carregar.
- Os resultados de validação e as amostras pessoais não são publicados neste repositório.



Siga o `README.md` para criar o ambiente `.venv`, baixar os modelos e gerar uma chave local própria. O Ollama deve ter `phi4-mini:latest` instalado. As medições de GPU acima descrevem a máquina do piloto; não são requisitos de hardware.

Fontes: https://portal.uern.br/blog/tag/educa/ e edital 019/2026 fornecido pelo usuário. Consulte os URLs de cada artigo em `data/documents.json`.
