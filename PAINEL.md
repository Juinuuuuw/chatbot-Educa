# Painel de atendimento da EdUCA

Nesta branch, o painel funciona com a extensão e a API local. A conexão com o WhatsApp fica no navegador; a fila, o histórico e as decisões de atendimento ficam na API. Não há serviços pagos, fontes externas ou bibliotecas carregadas de uma CDN na interface.

## Neste computador

1. Abra `INICIAR-LOCAL.cmd` nesta pasta. A cópia foi configurada na porta **8766**, separada da API original na porta 8765.
2. No Brave, abra `brave://extensions`. Desative a extensão antiga para não ter duas versões respondendo à mesma conversa. Ative o modo de desenvolvedor e carregue a pasta `extension` desta cópia.
3. Mantenha o WhatsApp Web aberto e conectado à sua conta. No popup da extensão, clique em **Conectar todas as conversas**. Não é necessário selecionar um contato: as novas mensagens individuais serão detectadas e cadastradas automaticamente. Grupos, comunidades, canais, status/listas de transmissão e a conversa da própria conta ficam excluídos.
4. O painel abre autenticado. Peça a um contato para enviar uma nova mensagem de texto ou áudio. O chat aparecerá no painel, com a Lia atendendo. Para reabrir, use **Abrir painel da EdUCA** na extensão. O acesso dura oito horas; a chave da API não aparece na interface nem é salva no navegador do painel.

A versão 0.6.0 da extensão descobre conversas individuais existentes e contatos novos. O registro no painel acontece quando há uma mensagem nova após a ativação. Mensagens anteriores, mesmo não lidas, não disparam respostas retroativas. O WhatsApp pode estar aberto em outra conversa; não é preciso clicar no contato recebido. O modo de seleção manual continua disponível dentro de **Teste individual e seleção manual** no popup.

Para ver somente o visual: `http://127.0.0.1:8766/panel/#demo=1`. Os contatos e as respostas dessa demonstração são fictícios; suas ações não enviam mensagens.

Use **Shift + E** para entrar ou sair da demonstração. O atalho não é acionado enquanto você digita em um campo ou está com um diálogo aberto. O botão circular no canto superior direito abre a acessibilidade, incluindo o modo escuro. A lateral mantém os filtros das filas, **Concluídas** e **Relatórios**, sem os antigos cartões da assistente ou botões de demonstração. A logo muda para uma versão transparente com letras claras no tema escuro.

O botão **Pausar conexão do painel** interrompe a coleta e o envio pela extensão. As respostas já preparadas permanecem na fila; antes de retomar, confira as conversas. O teste individual antigo só pode ser ativado com a conexão do painel pausada.

## Fluxo de atendimento

- **Com a Lia:** reúne mensagens durante cinco segundos sem novas mensagens detectadas, responde por texto ou voz e mostra o histórico no painel. Áudios demorados recebem um aviso de espera pré-gravado.
- **Aguardando equipe:** pedidos de atendente, assuntos individuais/restritos, informação sem fonte e falhas de processamento entram nessa fila. O painel mostra o motivo, destaca a fila e atualiza a contagem no título da aba.
- **Em atendimento:** clique em **Assumir conversa**. A Lia fica pausada nesse chat; respostas dela ainda em preparação são descartadas e as que não começaram a ser enviadas são canceladas. Você pode escrever, gravar um áudio, ouvir a prévia e enviar.
- **Devolver à Lia:** libera o atendimento automático para as próximas mensagens. Não responde retroativamente às perguntas recebidas enquanto a equipe atendia.
- **Concluir atendimento:** encerra a sessão; uma nova mensagem do contato reabre o atendimento com a Lia.

Uma mensagem manual enviada diretamente no WhatsApp também coloca o chat em atendimento humano. Um envio que já começou pode terminar mesmo depois de assumir a conversa. O status de cada resposta aparece no histórico: na fila, enviando, enviado, cancelado ou incerto. Um envio incerto **não é repetido automaticamente**; confira o WhatsApp antes de continuar.

## Interface e acessibilidade

Identidade visual baseada na logo fornecida: fundos neutros, azul para as ações e laranja discreto para os chamados. Tema claro/escuro, contraste aumentado, texto ampliável, movimento reduzido, navegação por teclado e skeletons de carregamento. Preferências são salvas neste navegador. O sistema respeita a preferência de movimento reduzido do dispositivo.

O painel atualiza a cada três segundos. A extensão verifica mensagens a cada cinco segundos com a aba do WhatsApp aberta; suspensão da aba ou do computador pode aumentar esse intervalo. A gravação pede permissão para usar o microfone e para automaticamente em três minutos. A mensagem só vai para a fila após clicar em enviar.

## Dados e limites do protótipo

O resumo das filas fica na barra lateral, liberando a área principal para as conversas. Na demonstração, o aviso aparece por sete segundos a cada dois minutos; o indicador de demonstração continua no cabeçalho.

O botão **Relatórios** abre os indicadores de hoje ou dos últimos 7, 30 ou 90 dias: mensagens recebidas por texto/áudio, contatos distintos, encaminhamentos, assuntos e cursos mencionados, volume diário e motivos de encaminhamento. É possível exportar os dados em CSV. A classificação usa palavras-chave nas mensagens e nas transcrições; uma mensagem pode contar em mais de uma categoria. Não são números de matrículas ou vagas, nem confirmação de oferta de um curso. Os indicadores ficam guardados por até 90 dias, sem texto, áudio, nome ou telefone nas tabelas de indicadores. A contagem começa nos atendimentos registrados pelo painel; o histórico disponível no momento da atualização também é contabilizado. Encaminhamentos anteriores à implementação do relatório não são reconstruídos.

O histórico e os áudios do painel são guardados em `data/panel.sqlite3`, com limpeza de mensagens finalizadas após 24 horas. As conversas cadastradas continuam registradas. Mensagens pendentes não são apagadas para evitar perder a fila. O arquivo não é versionado. O modo automático inclui qualquer conversa individual que receba novas mensagens após a ativação; não importa o histórico anterior. No número pessoal, isso inclui contatos pessoais.

Executa apenas neste computador, em `127.0.0.1`. Ainda não há contas individuais de atendentes, distribuição por funcionário nem acesso em rede. O modelo e a geração de voz compartilham o computador; várias conversas podem entrar na fila, mas o processamento local de IA é serializado.

Uma futura integração oficial substitui o transporte da extensão, mantendo o contrato de entrada, fila e confirmação de envio. Ainda precisará de implementação e testes próprios.

## Validação

Testes de API cobrem autenticação, origem, acesso por ticket de uso único, deduplicação, fila, intervenção durante geração, transcrição no atendimento humano, áudio do atendente e envio incerto. Testes simulados da extensão cobrem múltiplos contatos e grupos de mensagens. A interface foi verificada no Brave em tema claro/escuro e larguras de 390, 768, 1024 e 1440 pixels.

Esses testes não enviam mensagens reais. O teste de ponta a ponta no WhatsApp exige carregar a nova extensão, conectar todas as conversas e receber uma mensagem de teste.

A descoberta usa a [listagem individual da WA-JS](https://wppconnect.io/wa-js/functions/chat.list.html), com filtro adicional por tipo de conversa e identidade da própria conta. Os testes também conferem contatos novos, mensagens antigas não lidas, mensagens recebidas no segundo de ativação e exclusão de grupos/status.
