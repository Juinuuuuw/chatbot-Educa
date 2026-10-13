"""Apêndice independente. Sua exclusão não altera os capítulos do documento base."""

def build_panel(context, first_page=16):
    Page=context['Page']; Drawing=context['Drawing']; WIDTH=context['WIDTH']
    node=context['node']; arrow=context['arrow']; String=context['String']
    SMALL=context['SMALL']; REF=context['REF']

    p=Page(first_page,'APÊNDICE A - PAINEL DE ATENDIMENTO DA EDUCA')
    p.subheading('A.1 Finalidade e organização')
    p.para('Este apêndice apresenta a ampliação opcional do protótipo para acompanhamento e atendimento pela equipe da EdUCA. Os capítulos anteriores registram a versão individual originalmente documentada. Aqui, descreve-se a implementação da branch feat/painel-atendimento, consultada em 13 de outubro de 2026, com extensão na versão 0.6.0. Os controles descritos neste apêndice se aplicam ao modo painel; o teste individual continua disponível separadamente.')
    p.para('O painel reúne as conversas recebidas pelo WhatsApp Web, mostra o histórico e permite que uma pessoa da equipe assuma o atendimento. A extensão continua responsável pela conexão com o WhatsApp; a API organiza as conversas, as respostas e a fila de envio. A equipe utiliza a interface web, enquanto a sessão do WhatsApp permanece aberta no navegador.')
    d=Drawing(WIDTH,171)
    for x,text in [(0,'WhatsApp Web\nConta conectada'),(159,'Extensão 0.6.0\nConversas individuais'),(318,'API local\nFila e processamento')]:
        node(d,x,111,WIDTH-318,50,text)
    arrow(d,WIDTH-318,136,159,136);arrow(d,159+WIDTH-318,136,318,136)
    node(d,318,19,WIDTH-318,50,'Painel web\nEquipe da EdUCA')
    node(d,159,19,WIDTH-318,50,'Lia\nRegras, RAG e voz')
    node(d,0,19,WIDTH-318,50,'SQLite\nHistórico e indicadores')
    arrow(d,318+(WIDTH-318)/2,111,318+(WIDTH-318)/2,69)
    arrow(d,342,111,159+(WIDTH-318)/2,69)
    arrow(d,326,111,(WIDTH-318)/2,69)
    p.figure(d,'Componentes do painel e conexão com o protótipo',8)
    p.para('Ao clicar em “Conectar todas as conversas”, a extensão identifica mensagens novas em conversas individuais, inclusive de contatos ainda não cadastrados no painel. Grupos, comunidades, canais, status, listas de transmissão e a conversa da própria conta são excluídos. O histórico anterior à ativação, mesmo quando não lido, não dispara respostas retroativas.')
    p.para('A seção foi mantida após as referências para permitir sua retirada sem alterar a numeração dos capítulos principais. Também existe uma versão separada deste apêndice. Na fonte do documento, a opção --sem-painel gera a versão base sem o apêndice e sem sua entrada no sumário.',SMALL)
    p.finish()

    p=Page(first_page+1,'A.2 CONTROLE DAS CONVERSAS E INTERVENÇÃO HUMANA')
    p.para('Cada conversa recebe um estado de atendimento: com a Lia, aguardando a equipe, em atendimento humano ou concluída. Um pedido de atendente, uma questão que depende de avaliação da equipe ou uma falha no processamento pode levar o chat à fila de espera. O motivo aparece no painel; a contagem da fila também é apresentada no título da aba.')
    d=Drawing(WIDTH,181)
    node(d,0,125,130,43,'Com a Lia\nResposta automática')
    node(d,166,125,130,43,'Aguardando equipe\nPedido ou avaliação')
    node(d,332,125,WIDTH-332,43,'Em atendimento\nPessoa da equipe')
    arrow(d,130,146.5,166,146.5);arrow(d,296,146.5,332,146.5)
    node(d,332,24,WIDTH-332,43,'Concluída')
    arrow(d,430,125,430,67)
    arrow(d,390,125,390,94);arrow(d,390,94,65,94);arrow(d,65,94,65,125)
    d.add(String(200,78,'Devolver à Lia',fontName='TimesNewRoman',fontSize=10,textAnchor='middle'))
    arrow(d,332,45.5,20,45.5);arrow(d,20,45.5,20,125)
    d.add(String(176,17,'Nova mensagem reabre o atendimento',fontName='TimesNewRoman',fontSize=10,textAnchor='middle'))
    p.figure(d,'Estados da conversa no modo painel',9)
    p.para('Ao assumir uma conversa, a pessoa da equipe pausa a Lia naquele chat. As respostas automáticas ainda em preparação são descartadas, e as que não começaram a ser enviadas são canceladas. Um envio já iniciado pode terminar. O atendente pode escrever uma resposta ou gravar um áudio, ouvir a prévia e confirmar o envio.')
    p.para('A ação “Devolver à Lia” libera as próximas mensagens para atendimento automático. As perguntas recebidas durante o atendimento humano não são respondidas retroativamente. A ação “Concluir atendimento” encerra a sessão; uma mensagem posterior do contato reabre o chat com a Lia. Mensagens manuais enviadas diretamente no WhatsApp também colocam a conversa em atendimento humano.')
    p.para('Mensagens sucessivas são reunidas após cinco segundos sem nova entrada detectada. Havendo áudio, a resposta é falada. O painel reutiliza o processamento da API; nesta implementação, a transcrição utiliza Whisper e a geração de voz utiliza Chatterbox PT-BR no computador. Áudios de espera previamente preparados podem ser enviados durante uma geração demorada.')
    p.para('A extensão reserva cada saída antes de enviá-la e informa o resultado à API. O histórico distingue mensagens na fila, em envio, enviadas, canceladas e com envio incerto. Um resultado incerto não é repetido automaticamente: a equipe deve conferir o WhatsApp antes de continuar.')
    p.finish()

    p=Page(first_page+2,'A.3 INTERFACE, ACESSIBILIDADE E RESUMO DO PEDIDO')
    p.para('A interface utiliza HTML, CSS e JavaScript, sem dependências de uma rede de distribuição de conteúdo. A identidade visual combina tons neutros com o azul e o laranja da EdUCA. O tema escuro utiliza uma adaptação transparente da logo, com letras claras. A Figura 10 representa a distribuição dos elementos na visualização de computador.')
    d=Drawing(WIDTH,176)
    node(d,0,10,88,155,'Navegação\nFilas\nConcluídas\nRelatórios')
    node(d,102,141,WIDTH-102,24,'Atendimento                              Acessibilidade')
    node(d,102,10,105,119,'Lista de chats\nBusca por nome\nFiltros de estado')
    node(d,221,10,128,119,'Histórico\nTexto e áudio\nCampo de resposta')
    node(d,363,10,WIDTH-363,119,'Contato\nResumo do pedido\nAções da equipe')
    p.figure(d,'Organização da interface do painel',10)
    p.table(['Recurso','Funcionamento'],[
        ('Acessibilidade','Botão no canto superior direito para tema escuro, contraste aumentado e tamanho do texto.'),
        ('Movimento reduzido','Desativa animações e respeita a preferência correspondente do dispositivo.'),
        ('Teclado','Tab e Enter permitem navegação; Shift + E alterna a demonstração fora de campos de edição e diálogos.'),
        ('Carregamento','Skeletons indicam a espera pelos dados, sem preencher a interface com resultados fictícios.'),
        ('Demonstração','Usa conversas fictícias. Um aviso aparece por sete segundos a cada dois minutos; nenhuma mensagem é enviada.')
    ],[110,WIDTH-110],'Quadro 4 - Recursos de interface e acessibilidade')
    p.para('O bloco “Lia e você, juntos” aparece apenas em conversas aguardando a equipe ou em atendimento humano. Ele reúne trechos dos pedidos recentes da pessoa, incluindo as transcrições disponíveis. Trata-se de um resumo por seleção do texto recebido, não de uma conclusão produzida pelo modelo sobre a situação do contato.')
    p.para('As preferências ficam salvas no navegador. No computador, listas e histórico rolam internamente; em telas menores, a interface se adapta.')
    p.finish()

    p=Page(first_page+3,'A.4 RELATÓRIOS E PERSISTÊNCIA DOS DADOS')
    p.para('A área de relatórios permite observar a procura da comunidade em períodos de hoje, sete, trinta ou noventa dias. Os dados podem ser exportados em CSV para análise em planilhas. A demonstração identifica seus números como fictícios, mantendo-os separados dos indicadores dos atendimentos reais.')
    p.table(['Indicador','Interpretação'],[
        ('Mensagens recebidas','Quantidade de entradas dos contatos, separadas entre texto e áudio; não inclui as respostas do bot ou da equipe.'),
        ('Contatos distintos','Número de identificadores de contato diferentes no período, sem somar novamente a mesma pessoa a cada dia.'),
        ('Uso de áudio','Proporção de mensagens de áudio em relação ao total de mensagens recebidas.'),
        ('Assuntos e cursos','Menções reconhecidas por palavras-chave no texto e nas transcrições disponíveis.'),
        ('Volume diário','Distribuição das mensagens pelos dias do período selecionado.'),
        ('Encaminhamentos','Ocorrências registradas por pedido de atendente, avaliação da equipe ou falha de processamento ou integração.')
    ],[114,WIDTH-114],'Quadro 5 - Indicadores disponíveis no painel')
    p.para('Uma mensagem pode mencionar mais de um assunto ou curso. A classificação é lexical e não equivale a uma análise completa de intenção. Áudios sem transcrição disponível não contribuem para a identificação dos temas. Uma menção a um curso informa interesse, sem comprovar sua oferta, matrícula ou disponibilidade de vagas.')
    p.para('O painel utiliza o banco local panel.sqlite3. Mensagens finalizadas e seus áudios são limpos após vinte e quatro horas; saídas pendentes permanecem na fila. Os indicadores são conservados por até noventa dias em registros separados, sem armazenar o texto, o arquivo de áudio, o nome ou o telefone nessas tabelas. Identificadores transformados por hash permitem evitar duplicações e contar contatos distintos.')
    p.para('A contagem começa nos atendimentos registrados pelo painel. O histórico ainda disponível no banco durante a atualização pode ser incluído nos indicadores de demanda. Encaminhamentos ocorridos antes da implementação dos relatórios não são reconstruídos; os números não devem ser apresentados como uma série histórica completa da EdUCA.')
    p.finish()

    p=Page(first_page+4,'A.5 OPERAÇÃO, VALIDAÇÃO E LIMITES')
    p.para('A cópia do projeto está na branch feat/painel-atendimento e executa a API em 127.0.0.1:8766. A porta separa esse protótipo da versão individual anterior. O computador deve manter o Ollama, a API e o WhatsApp Web disponíveis. A extensão precisa estar carregada no Brave e ser ativada pelo botão “Conectar todas as conversas”.')
    p.para('O acesso ao painel é aberto pela extensão com um código temporário de uso único. A sessão de acesso dura oito horas e não expõe a chave da API na interface. A instalação atual funciona neste computador; não há contas individuais de atendentes, distribuição por funcionário nem acesso da equipe por uma rede local já configurada.')
    p.para('O painel consulta atualizações a cada três segundos. A extensão verifica mensagens aproximadamente a cada cinco segundos e evita consultar novamente chats sem alterações a cada ciclo. A suspensão da aba ou do computador pode ampliar os intervalos. O processamento de inteligência artificial é serializado, pois as conversas compartilham os recursos da máquina.')
    p.para('Os testes locais verificaram autenticação, descoberta de contatos novos, exclusão de grupos e da própria conta, mensagens antigas não lidas, agrupamento de texto e áudio, deduplicação e pausa. Também foram conferidos a intervenção durante a preparação de uma resposta, os estados de envio e os relatórios. A interface e o popup foram avaliados no Brave com integrações simuladas.')
    p.para('Essas verificações não constituem um teste completo de envio pela conta pessoal nem validam o uso institucional. O teste de ponta a ponta exige ativar a extensão na sessão real e conferir a entrada, a resposta da Lia e a continuidade pela equipe. Falhas na sessão do WhatsApp podem afetar o atendimento; um chat com erro deve permanecer visível para conferência.')
    p.para('A integração ainda depende da extensão e do WhatsApp Web. Uma adoção futura da API oficial exigirá implementar e testar outro transporte de entrada e saída. A organização em interface, API e fila permite preservar os estados do atendimento e o processamento da Lia durante essa mudança, mas não torna a migração automática.')
    p.subheading('Fonte da implementação')
    p.para('MEDEIROS, Juino. <b>Chatbot EdUCA: painel de atendimento</b>. Código-fonte e testes da branch feat/painel-atendimento, revisão 57e4106. 2026. Disponível em: https://github.com/Juinuuuuw/chatbot-Educa. Consulta ao código local em: 13 out. 2026.',REF,gap=0)
    p.finish()
