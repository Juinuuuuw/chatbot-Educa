from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics import renderPDF

import argparse
args_parser=argparse.ArgumentParser(description='Relatório ABNT com capítulo integrado do painel.')
mode=args_parser.add_mutually_exclusive_group()
mode.add_argument('--sem-painel',action='store_true')
mode.add_argument('--somente-painel',action='store_true')
args_parser.add_argument('--saida',type=Path)
args=args_parser.parse_args()
ROOT=Path(__file__).resolve().parents[2]
(ROOT/'outputs').mkdir(exist_ok=True)
OUT=ROOT/'outputs'/('Painel_Educa_ABNT.pdf' if args.somente_painel else 'Chatbot_Educa_ABNT.pdf')
if args.saida:OUT=args.saida.resolve()
OUT.parent.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('TimesNewRoman','C:/Windows/Fonts/times.ttf'))
pdfmetrics.registerFont(TTFont('TimesNewRomanBold','C:/Windows/Fonts/timesbd.ttf'))
pdfmetrics.registerFontFamily('TimesNewRoman',normal='TimesNewRoman',bold='TimesNewRomanBold',italic='TimesNewRoman',boldItalic='TimesNewRomanBold')
CM=72/2.54;W,H=595.276,841.89
LEFT=TOP=3*CM;RIGHT=BOTTOM=2*CM;WIDTH=W-LEFT-RIGHT
BODY=ParagraphStyle('body',fontName='TimesNewRoman',fontSize=12,leading=18,alignment=TA_JUSTIFY,firstLineIndent=1.25*CM)
SMALL=ParagraphStyle('small',fontName='TimesNewRoman',fontSize=10,leading=12,alignment=TA_LEFT)
REF=ParagraphStyle('reference',parent=SMALL,spaceAfter=12)
CELL=ParagraphStyle('cell',parent=SMALL,alignment=TA_LEFT)
HEADER=ParagraphStyle('header',parent=CELL,fontName='TimesNewRomanBold')
c=canvas.Canvas(str(OUT),pagesize=(W,H));c.setTitle('LIA COMO ASSISTENTE VIRTUAL DA EDUCA');c.setAuthor('Unidade Curricular de Extensão - Professora Glaucia');c.setSubject('Relatório técnico sobre arquitetura e funcionamento do protótipo')

class Page:
 def __init__(self,n,title=None,numbered=True):
  self.n=n;self.y=H-TOP
  if numbered:
   c.setFont('TimesNewRoman',10);c.drawRightString(W-RIGHT,H-2*CM,str(n))
  if title:self.heading(title)
 def heading(self,text,center=False):
  style=ParagraphStyle('heading',fontName='TimesNewRomanBold',fontSize=12,leading=18,alignment=TA_CENTER if center else TA_LEFT)
  p=Paragraph(escape(text),style);_,h=p.wrap(WIDTH,100);p.drawOn(c,LEFT,self.y-h);self.y-=h+18
 def subheading(self,text):self.heading(text)
 def para(self,text,style=None,gap=6):
  p=Paragraph(text,style or BODY);_,h=p.wrap(WIDTH,800)
  assert self.y-h>=BOTTOM,(self.n,text[:70],self.y,h)
  p.drawOn(c,LEFT,self.y-h);self.y-=h+gap
 def figure(self,d,title,number):
  self.para(f'Figura {number} - {escape(title)}',SMALL,gap=5)
  assert self.y-d.height>=BOTTOM+20,(self.n,self.y,d.height)
  renderPDF.draw(d,c,LEFT,self.y-d.height);self.y-=d.height+4
  self.para('Fonte: elaboração própria (2026).',SMALL,gap=16)
 def table(self,headers,rows,widths,title):
  self.para(title,SMALL,gap=5)
  data=[[Paragraph(escape(str(x)),HEADER) for x in headers]]+[[Paragraph(escape(str(x)),CELL) for x in row] for row in rows]
  t=Table(data,colWidths=widths)
  t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeee')),('GRID',(0,0),(-1,-1),.5,colors.HexColor('#999999')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
  _,h=t.wrap(WIDTH,800);assert self.y-h>=BOTTOM+25,(self.n,self.y,h)
  t.drawOn(c,LEFT,self.y-h);self.y-=h+4
  self.para('Fonte: elaboração própria (2026).',SMALL,gap=16)
 def finish(self):c.showPage()

def node(d,x,y,w,h,text):
 d.add(Rect(x,y,w,h,fillColor=colors.white,strokeColor=colors.black,strokeWidth=.65))
 lines=text.split('\n');top=y+h/2+(len(lines)-1)*6
 for i,line in enumerate(lines):
  assert pdfmetrics.stringWidth(line,'TimesNewRoman',10)<=w-6,(line,w)
  d.add(String(x+w/2,top-i*12-3,line,fontName='TimesNewRoman',fontSize=10,textAnchor='middle',fillColor=colors.black))
def arrow(d,x1,y1,x2,y2):
 d.add(Line(x1,y1,x2,y2,strokeColor=colors.black,strokeWidth=.65))
 dx=x2-x1;dy=y2-y1;l=(dx*dx+dy*dy)**.5;ux=dx/l;uy=dy/l;bx=x2-5*ux;by=y2-5*uy
 d.add(Polygon([x2,y2,bx-2*uy,by+2*ux,bx+2*uy,by-2*ux],fillColor=colors.black,strokeColor=colors.black))
def center_line(text,y,bold=False):
 c.setFont('TimesNewRomanBold' if bold else 'TimesNewRoman',12);c.drawCentredString(LEFT+WIDTH/2,y,text)

if not args.somente_painel:
 # Cover is counted as the first sheet, according to the pagination requested.
 p=Page(1,numbered=False)
 center_line('UNIVERSIDADE DO ESTADO DO RIO GRANDE DO NORTE',H-TOP-18)
 center_line('UNIDADE CURRICULAR DE EXTENSÃO',H-TOP-42)
 center_line('PROFESSORA GLAUCIA',H-TOP-66)
 center_line('LIA COMO ASSISTENTE VIRTUAL DA EDUCA',H*.58,bold=True)
 center_line('Arquitetura e funcionamento do protótipo',H*.58-24)
 center_line('Natal',BOTTOM+36);center_line('2026',BOTTOM+18);p.finish()

 p=Page(2,numbered=False)
 center_line('UNIVERSIDADE DO ESTADO DO RIO GRANDE DO NORTE',H-TOP-18)
 center_line('UNIDADE CURRICULAR DE EXTENSÃO',H-TOP-42)
 center_line('PROFESSORA GLAUCIA',H-TOP-66)
 center_line('LIA COMO ASSISTENTE VIRTUAL DA EDUCA',H*.65,bold=True)
 center_line('Arquitetura e funcionamento do protótipo',H*.65-24)
 note=Paragraph('Relatório técnico elaborado no âmbito de uma Unidade Curricular de Extensão (UCE), sob orientação da professora Glaucia, sobre o desenvolvimento de uma assistente virtual para a EdUCA no Campus de Natal da UERN.',ParagraphStyle('nature',fontName='TimesNewRoman',fontSize=12,leading=12,alignment=TA_JUSTIFY))
 _,nh=note.wrap(WIDTH/2,300);note.drawOn(c,LEFT+WIDTH/2,H*.47-nh)
 center_line('Natal',BOTTOM+36);center_line('2026',BOTTOM+18);p.finish()

 p=Page(3,numbered=False);p.heading('RESUMO',center=True)
 summary='O atendimento pelo WhatsApp permite que o público procure informações por texto e por mensagens de voz. Este relatório descreve Lia, um protótipo de assistente virtual para a EdUCA no Campus de Natal, desenvolvido com uma extensão para navegadores baseados em Chromium e uma API em Python. O atendimento combina regras para informações previamente verificadas com recuperação de trechos de documentos oficiais e geração de respostas pelo modelo Phi-4 Mini, executado por meio do Ollama. A base reúne o edital de matrícula do semestre 2026.2 e notícias do portal da Universidade do Estado do Rio Grande do Norte. A busca utiliza BM25, enquanto os dados das turmas são organizados separadamente para evitar confusão com notícias de outros períodos. Mensagens de voz são transcritas localmente pelo Whisper, e as respostas faladas são geradas localmente pelo Kokoro, com a voz Dora. O painel web reúne as conversas e permite a continuidade do atendimento pela equipe. Os testes verificaram respostas combinadas, histórico por conversa, formato de áudio e execução do modelo na GPU. O protótipo fornece orientação, mas não realiza matrícula, não consulta vagas em tempo real e não substitui decisões da equipe. Pedidos de atendimento humano são organizados em uma fila, sem atribuição automática a um funcionário. Sua utilização institucional depende de avaliação do funcionamento na sessão do WhatsApp e de acompanhamento das informações da base.'
 p.para(summary,ParagraphStyle('summary',parent=BODY,firstLineIndent=0),gap=18)
 p.para('<b>Palavras-chave:</b> chatbot; WhatsApp; recuperação de informações; modelo de linguagem; atendimento.',ParagraphStyle('keywords',parent=BODY,firstLineIndent=0));p.finish()

 p=Page(4,numbered=False);p.heading('SUMÁRIO',center=True)
 contents=[('1 INTRODUÇÃO',5),('2 ARQUITETURA E TECNOLOGIAS',6),('3 FUNCIONAMENTO DA EXTENSÃO',7),('4 RECUPERAÇÃO DE INFORMAÇÕES',8),('5 PROCESSAMENTO DE ÁUDIO',9),('6 HISTÓRICO E CONTROLE DO ATENDIMENTO',10),('7 VALIDAÇÃO E OPERAÇÃO',11),('8 LIA: IDENTIDADE E FLUXO DE ATENDIMENTO',12),('9 ESCOPO DAS RESPOSTAS',13),('10 CONSIDERAÇÕES FINAIS',14),('REFERÊNCIAS',15)]
 if not args.sem_painel:
  contents=contents[:-2]+[('10 PAINEL DE ATENDIMENTO',14),('11 CONSIDERAÇÕES FINAIS',20),('REFERÊNCIAS',21)]
 for title,page in contents:
  c.setFont('TimesNewRoman',12);c.drawString(LEFT,p.y-12,title);c.drawRightString(W-RIGHT,p.y-12,str(page))
  start=LEFT+pdfmetrics.stringWidth(title,'TimesNewRoman',12)+8;end=W-RIGHT-24
  c.setLineWidth(.4);c.setDash(1,3);c.line(start,p.y-13,end,p.y-13);c.setDash();p.y-=36
 p.finish()

 p=Page(5,'1 INTRODUÇÃO')
 p.para('O Educa oferece cursos e atividades de extensão no Campus de Natal da Universidade do Estado do Rio Grande do Norte. As dúvidas do público envolvem, entre outros assuntos, faixa de idade, horário das aulas, gratuidade e matrícula. O edital 019/2026 reúne as condições previstas para o semestre 2026.2 (FUNCITERN; UERN, 2026).')
 p.para('O protótipo documentado neste relatório foi desenvolvido para responder a essas perguntas em uma conversa do WhatsApp Web. Sua estrutura reúne uma extensão em navegador baseado em Chromium e uma API executada no computador. A extensão recebe as mensagens e envia as respostas; a API consulta a base, aplica regras e, quando necessário, solicita uma resposta ao modelo de linguagem.')
 d=Drawing(WIDTH,165);xs=[0,120,240,360];ww=WIDTH-360
 labels=['WhatsApp Web\nTexto ou áudio','Extensão\nJavaScript e WA-JS','API local\nPython e FastAPI','Regras e RAG\nPhi-4 Mini']
 for i,(x,label) in enumerate(zip(xs,labels)):
  w=103 if i<3 else ww;node(d,x,89,w,55,label)
  if i<3:arrow(d,x+w,116.5,xs[i+1],116.5)
 arrow(d,360+ww/2,89,360+ww/2,34);arrow(d,360+ww/2,34,51.5,34);arrow(d,51.5,34,51.5,89)
 d.add(String(WIDTH/2,10,'A resposta retorna pela API e pela extensão',fontName='TimesNewRoman',fontSize=10,textAnchor='middle'))
 p.figure(d,'Arquitetura geral do chatbot',1)
 p.para('A Figura 1 apresenta o caminho de entrada e saída das mensagens. O atendimento aceita texto e áudio, mantém um histórico curto por conversa e combina respostas controladas com recuperação de informações. O uso de áudio foi incluído para permitir que a pessoa escolha como se comunicar, sem pressupor dificuldades de leitura ou escrita.')
 p.para('O sistema tem função de orientação. Ele não realiza matrícula nem confirma vagas disponíveis. O modo painel acompanha novas mensagens em conversas individuais e permite que a equipe assuma o atendimento quando necessário. Grupos e a conversa da própria conta ficam excluídos. Há também um modo de teste individual para conferência do protótipo.')
 p.finish()

 p=Page(6,'2 ARQUITETURA E TECNOLOGIAS')
 p.para('A extensão foi escrita em JavaScript, com interface em HTML e CSS e Manifest V3. Sua estrutura utiliza APIs de extensões Chromium, presentes em Chrome, Edge e Brave (MICROSOFT, s.d.). A compatibilidade esperada precisa ser conferida em cada navegador; os testes do protótipo utilizaram Brave. A API utiliza Python e FastAPI (FASTAPI, s.d.).')
 p.table(['Componente','Tecnologia','Função'],[
 ('Extensão','JavaScript','Receber mensagens e controlar a comunicação com a API.'),
 ('Interface','HTML e CSS','Exibir ativação, pausa e andamento do atendimento.'),
 ('WhatsApp Web','WA-JS 4.6.1','Consultar mensagens e enviar texto ou áudio.'),
 ('API','Python e FastAPI','Aplicar regras e organizar busca, histórico e áudio.'),
 ('Modelo','Phi-4 Mini e Ollama','Gerar respostas com apoio dos trechos recuperados.'),
 ('Busca','rank-bm25','Classificar os trechos por relevância lexical.'),
 ('Extração','pypdf e BeautifulSoup','Ler o edital e extrair o conteúdo do portal.'),
 ('Persistência','JSON e SQLite','Guardar a base, respostas e histórico curto.'),
 ('Transcrição','faster-whisper small','Converter o áudio recebido em texto na CPU.'),
 ('Voz','Kokoro e Dora','Gerar a resposta falada no computador.'),
 ('Conversão','PyAV e Opus','Preparar áudio em OGG/Opus para o envio.')
 ],[87,111,WIDTH-198],'Quadro 1 - Componentes e tecnologias do protótipo')
 p.para('A comunicação entre extensão e API utiliza requisições HTTP com dados em JSON. JavaScript e Python executam a lógica do sistema; HTML e CSS definem a apresentação do painel. Os arquivos JSON armazenam documentos e dados de turmas, enquanto SQLite registra o histórico e as respostas em cache.')
 p.para('O modelo de linguagem, a busca, a transcrição e a síntese de voz são executados no computador. Kokoro utiliza a voz feminina Dora, com processamento na CPU. Essa escolha evita enviar o texto da resposta a um serviço externo de síntese e preserva os recursos da GPU para o modelo de linguagem (HEXGRAD, s.d.; THEWH1TEAGLE, s.d.).')
 p.finish()

 p=Page(7,'3 FUNCIONAMENTO DA EXTENSÃO')
 p.para('Quando o atendimento é ativado, a extensão verifica a API e registra um ponto de partida para a leitura das conversas. No modo painel, novas mensagens de contatos individuais são identificadas sem exigir a seleção manual de cada chat. Mensagens anteriores à ativação não recebem respostas retroativas. A leitura e o envio utilizam WA-JS, biblioteca que opera sobre a sessão do WhatsApp Web (WPPCONNECT, s.d.).')
 d=Drawing(WIDTH,126);step=(WIDTH+12)/4;bw=step-12
 for i,text in enumerate(['Mensagem nova\nem chat individual','Filtros e IDs\nEvitar duplicação','POST /message\nConsulta à API','Resposta\nTexto ou áudio']):
  x=i*step;node(d,x,40,bw,55,text)
  if i<3:arrow(d,x+bw,67.5,x+step,67.5)
 p.figure(d,'Processamento de uma mensagem pela extensão',2)
 p.para('Lia é uma assistente híbrida: informações verificadas podem receber uma resposta direta por regras, enquanto outras perguntas exigem consulta aos documentos e uso da Phi. Uma mesma mensagem pode combinar assuntos, como gratuidade e faixa de idade. Nesse caso, o sistema reúne as informações necessárias para responder às partes reconhecidas da pergunta.')
 d=Drawing(WIDTH,166);node(d,126,119,200,37,'Pergunta e contexto da conversa')
 positions=[0,156,312];bw=141
 for x,text in zip(positions,['Regras\nResposta direta','Busca BM25\nTrechos oficiais','Dados insuficientes\nEsclarecimento']):node(d,x,51,bw,43,text)
 arrow(d,153,119,70,94);arrow(d,226,119,226,94);arrow(d,298,119,382,94)
 node(d,156,0,bw,31,'Phi-4 Mini');arrow(d,226,51,226,31)
 p.figure(d,'Decisão entre regras e modelo de linguagem',3)
 p.para('A resposta deve se limitar ao pedido atual. Uma pergunta sobre dia e horário não exige repetir idade, documentos ou disponibilidade de vagas. O histórico ajuda a identificar a turma mencionada anteriormente, mas não deve ampliar o assunto por conta própria.')
 p.finish()

 p=Page(8,'4 RECUPERAÇÃO DE INFORMAÇÕES')
 p.para('A recuperação de informações usada no projeto é conhecida como RAG. Em vez de treinar a Phi com o edital, a API seleciona trechos relacionados à pergunta e os envia ao modelo. A busca utiliza BM25, implementação disponível na biblioteca rank-bm25 (Brown, s.d.).')
 d=Drawing(WIDTH,175);xs=[0,159,318];bw=WIDTH-318
 for x,text in zip(xs,['Edital e notícias\nFontes oficiais','Extração e limpeza\nTexto dos documentos','Trechos e metadados\nData, origem e página']):node(d,x,109,bw,53,text)
 for i in range(2):arrow(d,xs[i]+bw,135.5,xs[i+1],135.5)
 for x,text in zip(xs,['Pergunta e contexto\nEnviados à Phi','BM25\nSeleção dos trechos','Base local\nArquivos JSON']):node(d,x,16,bw,53,text)
 arrow(d,318+bw/2,109,318+bw/2,69);arrow(d,318,42.5,159+bw,42.5);arrow(d,159,42.5,bw,42.5)
 p.figure(d,'Preparação da base e recuperação dos trechos',4)
 p.para('A ingestão registrada em 8 de outubro de 2026 reúne 17 documentos, correspondentes a sete páginas do edital e dez notícias do portal. A divisão produziu 34 trechos. A tabela do edital foi organizada separadamente em 20 registros de turmas, adicionados à recuperação pela API. Assim, a versão documentada pesquisa 54 itens.')
 p.para('A busca é lexical, baseada nas palavras da pergunta, sem embeddings ou banco vetorial. Os trechos preservam título, origem, data e, quando disponível, página. Para horário e idade das turmas, a API prioriza os dados da tabela, evitando misturar o edital com notícias de outros períodos.')
 p.para('A base não cobre todo o histórico do portal e não é atualizada durante cada atendimento. Novos documentos precisam passar pela ingestão, seguida de reinício da API. O edital previa início das aulas em 3 de agosto de 2026; essa previsão não comprova o início efetivo nem a abertura de novas inscrições (FUNCITERN; UERN, 2026).')
 p.finish()

 p=Page(9,'5 PROCESSAMENTO DE ÁUDIO')
 p.para('O processamento começa quando a extensão identifica uma mensagem de voz em uma conversa individual acompanhada. O áudio é enviado à API, que utiliza faster-whisper para obter a transcrição. Essa etapa ocorre no computador, na CPU (SYSTRAN, s.d.).')
 d=Drawing(WIDTH,184);xs=[0,159,318];bw=WIDTH-318
 for x,text in zip(xs,['Áudio recebido\nWhatsApp Web','Whisper small\nTranscrição local','Pergunta em texto\nRegras ou RAG']):node(d,x,115,bw,53,text)
 for i in range(2):arrow(d,xs[i]+bw,141.5,xs[i+1],141.5)
 for x,text in zip(xs,['Resposta no WhatsApp\nMensagem de voz','PyAV\nÁudio OGG/Opus','Kokoro / Dora\nSíntese local']):node(d,x,23,bw,53,text)
 arrow(d,318+bw/2,115,318+bw/2,76);arrow(d,318,49.5,159+bw,49.5);arrow(d,159,49.5,bw,49.5)
 p.figure(d,'Transcrição da entrada e geração da resposta falada',5)
 p.para('Depois de preparar a resposta, a API gera a fala com Kokoro e a voz Dora. O processamento é local, sem chamada ao serviço de voz da Microsoft. O fraseado conserva a pontuação da resposta, mantém saudações curtas com a frase seguinte e introduz pausas entre ideias. A velocidade pode ser ajustada sem alterar o conteúdo da orientação (HEXGRAD, s.d.; THEWH1TEAGLE, s.d.).')
 p.para('O áudio é convertido para OGG/Opus e enviado como mensagem de voz. Emojis são retirados e horários são preparados para leitura. As grafias Educa, EdUCA e EDUCA são normalizadas apenas no texto falado. Durante uma geração demorada, a extensão pode enviar um aviso pré-gravado com teclado sintético discreto, reduzido durante a fala. As respostas principais permanecem sem ruído de fundo.')
 p.para('O protótipo aceita áudios de até três minutos e 12 MB. Ruído, sotaque, nomes e números podem prejudicar a transcrição. Quando não entende o conteúdo, o bot pede uma repetição. Essas condições precisam ser avaliadas com mensagens reais antes de ampliar o atendimento.')
 p.finish()

 p=Page(10,'6 HISTÓRICO E CONTROLE DO ATENDIMENTO')
 p.para('A extensão registra os identificadores das mensagens processadas em cada conversa. As saídas do próprio bot também são reconhecidas, para impedir que ele responda a si mesmo. No modo painel, os estados do atendimento separam as conversas com a Lia das que dependem da equipe. Um resultado de envio incerto não é repetido automaticamente.')
 d=Drawing(WIDTH,158);xs=[0,165,330];bw=WIDTH-330
 for x,text in zip(xs,['Bot pausado','Conectar extensão\nAPI e sessão válidas','Bot ativo\nNovas mensagens']):node(d,x,101,bw,44,text)
 arrow(d,bw,123,165,123);arrow(d,165+bw,123,330,123)
 node(d,165,12,WIDTH-165,51,'Pausa geral, erro ou intervenção da equipe\nO envio incerto não é repetido automaticamente')
 arrow(d,330+bw/2,101,330+bw/2,63);arrow(d,165,37.5,bw/2,37.5);arrow(d,bw/2,37.5,bw/2,101)
 p.figure(d,'Ativação e pausa do atendimento',6)
 p.para('A API conserva até quatro pares de pergunta e resposta por conversa. As últimas duas trocas podem ser enviadas à Phi como contexto. Isso permite compreender perguntas como “E qual o horário?” depois de uma mensagem que identifica a turma. O histórico é separado por conversa e não é usado para treinar o modelo.')
 p.para('A comunicação entre extensão e API exige uma chave de acesso mantida nos arquivos de configuração. Os registros são guardados em SQLite, com retenção de vinte e quatro horas para o histórico finalizado. Perguntas e respostas permanecem legíveis no banco; o acesso a esses arquivos precisa ser controlado pela instituição.')
 p.para('Quando a pessoa pede um atendente, a conversa é direcionada à fila de espera da equipe. Ao assumir o chat, o atendente interrompe novas respostas da Lia naquela conversa e pode continuar por texto ou áudio. A pausa geral da extensão suspende o acompanhamento. Os estados e as ações da equipe são apresentados no capítulo sobre o painel.')
 p.para('A integração utiliza a sessão do WhatsApp Web e não a API oficial de atendimento. Mudanças na plataforma podem afetar o funcionamento, e existe risco de restrição da conta. O piloto precisa de acompanhamento antes de uso institucional.')
 p.finish()

 p=Page(11,'7 VALIDAÇÃO E OPERAÇÃO')
 p.para('Os testes locais verificaram o processamento da API, a aplicação de regras e a recuperação de informações. Foram usados casos com perguntas combinadas, continuação da conversa e solicitação de apenas um dado, como dia ou horário. O Quadro 2 apresenta o alcance dessas verificações.')
 p.table(['Verificação','Resultado e alcance'],[
 ('API e regras','Autenticação, menu da Lia, dez perguntas gerais, limites de atendimento e perguntas combinadas verificados localmente.'),
 ('Histórico','Continuidade, isolamento entre conversas, limite de quatro trocas e repetição da mesma requisição.'),
 ('Áudio','Síntese local Kokoro, leitura de OGG/Opus, cache de voz e transcrição verificados nos componentes locais.'),
 ('WhatsApp real','Respostas em texto e comportamento da voz relatados pelo usuário; a sessão real não é inteiramente coberta pelos testes locais.')
 ],[101,WIDTH-101],'Quadro 2 - Verificações realizadas no protótipo')
 p.para('A execução do modelo de linguagem pode utilizar a GPU quando o ambiente possui memória e suporte compatíveis. Caso contrário, o processamento pode ocorrer na CPU ou ser dividido entre os dois recursos. O Ollama gerencia esse carregamento conforme a configuração disponível. A busca e as regras continuam independentes da execução da Phi; a transcrição e a síntese Kokoro utilizam a CPU no perfil documentado.')
 p.para('O tempo de resposta depende do tamanho da pergunta, da quantidade de mensagens agrupadas, da recuperação dos documentos e dos recursos disponíveis. O uso de GPU pode acelerar a geração de texto, mas não elimina o tempo das outras etapas. A reutilização de uma resposta falada já preparada evita uma nova síntese quando o conteúdo e o perfil de voz são iguais.')
 p.para('Para atender, o ambiente de processamento, o Ollama, a API e a sessão do WhatsApp Web precisam estar disponíveis. A extensão conecta as conversas ao painel, onde a equipe acompanha as filas. Pausar a extensão interrompe novas respostas automáticas; encerrar a API desliga o processamento. Parâmetros de instalação podem ser ajustados sem alterar o fluxo do atendimento.')
 p.finish()

 p=Page(12,'8 LIA: IDENTIDADE E FLUXO DE ATENDIMENTO')
 p.para('A assistente virtual recebe o nome Lia. A escolha se deve a um nome curto, que remete a “ler” e soa muito bem em voz sintetizada. O nome identifica a assistente no painel da extensão e na apresentação inicial ao público. A voz feminina Dora é um recurso de síntese, sem imitar uma pessoa da equipe.')
 p.para('Uma saudação simples por texto, como “Oi” ou “Bom dia”, recebe uma apresentação e um menu numerado com dez assuntos. A pessoa pode escolher um número para obter uma resposta estática ou escrever sua pergunta livremente. O menu não é uma etapa obrigatória: perguntas completas são respondidas diretamente.')
 d=Drawing(WIDTH,171)
 node(d,139,125,174,34,'Nova mensagem para Lia')
 for x,text in zip([0,156,312],['Texto: saudação simples\nApresentação e menu','Texto: pergunta completa\nResposta direta','Áudio: transcrição\nResposta falada']):node(d,x,52,141,48,text)
 arrow(d,160,125,70,100);arrow(d,226,125,226,100);arrow(d,292,125,382,100)
 d.add(String(WIDTH/2,18,'Regras conferidas, consulta à base e limites de atendimento',fontName='TimesNewRoman',fontSize=10,textAnchor='middle'))
 p.figure(d,'Fluxo de atendimento da Lia por texto e áudio',7)
 p.para('Mensagens de áudio seguem a transcrição e recebem uma resposta falada, sem envio do menu. Se o áudio contiver apenas uma saudação, Lia se apresenta brevemente e pergunta como pode ajudar. Uma pergunta reconhecida pode ser respondida por regras; perguntas mais específicas podem utilizar a busca e o modelo de linguagem.')
 p.para('A redação deve ser acolhedora, simples e adequada ao pedido. Perguntas combinadas não devem perder partes da solicitação. O histórico serve para identificar uma turma já mencionada, sem repetir informações ou ampliar o assunto por conta própria.')
 p.finish()

 p=Page(13,'9 ESCOPO DAS RESPOSTAS')
 p.para('Lia atende às dúvidas gerais descritas no Quadro 3. As respostas estáticas usam as condições verificadas no edital e indicam quando a base não permite confirmar uma informação atual. A lista histórica de cursos não equivale à confirmação de oferta ou de vagas no momento da conversa.')
 p.table(['Assunto','Orientação da resposta'],[
 ('Cursos e atividades','Listar os registros do semestre 2026.2 e orientar a confirmação da oferta atual.'),
 ('Inscrição','Explicar o procedimento previsto e indicar que o prazo histórico já passou.'),
 ('Participação','Informar o público e os critérios de idade de cada turma, sem garantir matrícula.'),
 ('Gratuidade','Confirmar a gratuidade do edital; outros projetos dependem da divulgação específica.'),
 ('Dias e horários','Usar a tabela conferida; solicitar a turma quando ela não estiver identificada.'),
 ('Vagas','Orientar a consulta à equipe; não tratar números históricos como vagas atuais.'),
 ('Local','Informar o Complexo Cultural da UERN para as atividades previstas no edital.'),
 ('Documentos','Explicar a documentação prevista sem solicitar seu envio pelo chat.'),
 ('Certificado','Não prometer emissão; a base não estabelece uma regra geral de certificação.'),
 ('Novas turmas e projetos','Orientar o acompanhamento das divulgações oficiais, sem inventar datas.')
 ],[109,WIDTH-109],'Quadro 3 - Assuntos atendidos pela Lia')
 p.para('Questões que exigem análise ou decisão da equipe, informações internas, fatos não confirmados oficialmente e situações de atendimento individualizado devem ser encaminhadas como orientação para procurar a equipe da EdUCA. Lia não decide exceções, consulta cadastros, resolve recursos ou avalia condições pessoais de saúde.')
 p.para('No painel, pedidos de atendente e situações que dependem de análise da equipe entram na fila de espera. A continuidade depende de uma pessoa assumir a conversa. Lia não toma decisões institucionais, não identifica um funcionário disponível e não garante um prazo de resposta humana.')
 p.finish()

 if not args.sem_painel:
  from painel_abnt import build_panel
  build_panel(globals(),first_page=14)

 p=Page(14 if args.sem_painel else 20,('10' if args.sem_painel else '11')+' CONSIDERAÇÕES FINAIS')
 p.para('O protótipo reúne, em uma mesma conversa, respostas por regras, consulta a documentos e comunicação por áudio. A extensão permite aproveitar a sessão do WhatsApp Web, enquanto a API concentra a base e o processamento. Essa organização facilita a revisão das respostas e a atualização das fontes sem alterar toda a interface do navegador.')
 p.para('As regras são úteis para informações que podem ser conferidas diretamente, como gratuidade, faixa de idade e horário de uma turma. A recuperação de trechos amplia o conjunto de perguntas que pode ser respondido, mas o modelo ainda pode acrescentar detalhes desnecessários ou interpretar uma fonte de maneira inadequada. Por isso, as respostas precisam ser limitadas ao pedido atual e avaliadas com exemplos de uso real.')
 p.para('A disponibilidade de vagas e as datas de novas inscrições continuam dependendo de confirmação pela equipe. Uma previsão histórica do edital não permite anunciar inscrições abertas. O painel organiza os pedidos de atendimento humano e permite a continuidade pela equipe, mas não substitui a análise institucional nem garante que uma pessoa esteja disponível no momento da solicitação.')
 p.para('Antes de ampliar o piloto, é necessário acompanhar a integração com o WhatsApp, revisar os resultados da transcrição e manter a base atualizada. Também devem ser avaliados o acesso aos registros e a clareza da voz. A síntese local reduz a dependência de serviços externos. Essas verificações ajudam a estabelecer o que a assistente pode responder sozinha e o que deve permanecer sob responsabilidade da equipe.')
 p.finish()

 p=Page(15 if args.sem_painel else 21,numbered=True);p.heading('REFERÊNCIAS',center=True)
 refs=[
  'BROWN, Dorian. <b>rank_bm25: a collection of BM25 algorithms in Python</b>. [S. l.], [s. d.]. Disponível em: https://github.com/dorianbrown/rank_bm25. Acesso em: 8 out. 2026.',
  'FASTAPI. <b>FastAPI</b>. [S. l.], [s. d.]. Disponível em: https://fastapi.tiangolo.com/. Acesso em: 8 out. 2026.',
  'FUNCITERN; UNIVERSIDADE DO ESTADO DO RIO GRANDE DO NORTE. <b>Edital nº 019/2026 FUNCITERN PROEX UERN: matrículas de alunos para o semestre 2026.2</b>. Natal, 23 jul. 2026. 7 p. Documento fornecido para a base do protótipo.',
  'HEXGRAD. <b>Kokoro-82M: modelo e vozes de síntese</b>. [S. l.], [s. d.]. Disponível em: https://huggingface.co/hexgrad/Kokoro-82M. Acesso em: 13 out. 2026.',
  'MEDEIROS, Juino. <b>Chatbot EdUCA: painel de atendimento</b>. Código-fonte e testes da branch feat/painel-atendimento, revisão 1e9af68. 2026. Disponível em: https://github.com/Juinuuuuw/chatbot-Educa. Consulta ao código local em: 14 out. 2026.',
  'META. <b>Pricing on the WhatsApp Business Platform</b>. [S. l.], 2026. Disponível em: https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/. Acesso em: 14 out. 2026.',
  'MICROSOFT. <b>Overview of Microsoft Edge extensions</b>. [S. l.], [s. d.]. Disponível em: https://learn.microsoft.com/en-us/microsoft-edge/extensions/. Acesso em: 14 out. 2026.',
  'OLLAMA. <b>FAQ</b>. [S. l.], [s. d.]. Disponível em: https://docs.ollama.com/faq. Acesso em: 8 out. 2026.',
  'SYSTRAN. <b>faster-whisper: faster Whisper transcription with CTranslate2</b>. [S. l.], [s. d.]. Disponível em: https://github.com/SYSTRAN/faster-whisper. Acesso em: 8 out. 2026.',
  'THEWH1TEAGLE. <b>kokoro-onnx</b>. [S. l.], [s. d.]. Disponível em: https://github.com/thewh1teagle/kokoro-onnx. Acesso em: 13 out. 2026.',
  'UNIVERSIDADE DO ESTADO DO RIO GRANDE DO NORTE. <b>Portal UERN: notícias da tag Educa</b>. [S. l.], [s. d.]. Disponível em: https://portal.uern.br/blog/tag/educa/. Acesso em: 8 out. 2026.',
  'WHATSAPP. <b>How to use WhatsApp responsibly</b>. [S. l.], [s. d.]. Disponível em: https://faq.whatsapp.com/361005896189245/. Acesso em: 14 out. 2026.',
  'WPPCONNECT. <b>WA-JS: documentação da versão 4.6.1</b>. [S. l.], [s. d.]. Disponível em: https://wppconnect.io/wa-js/. Acesso em: 8 out. 2026.',
 ]
 for ref in refs:p.para(ref,REF,gap=8)
 p.finish()
if args.somente_painel:
 from painel_abnt import build_panel
 build_panel(globals(),first_page=1)
c.save();print(OUT)
