"""Menu e limites de atendimento da Lia; informações gerais conferidas no edital."""
import re
import unicodedata
import json
from pathlib import Path

LOCATION=json.loads((Path(__file__).resolve().parent/'data/location.json').read_text(encoding='utf-8'))
LOCATION_TEXT=('A EdUCA fica na '+LOCATION['campus']+'.\n'+LOCATION['address']+
               '\nComo chegar: '+LOCATION['maps_url'])
LOCATION_SOURCE={'title':LOCATION['source'],'url':LOCATION['maps_url'],'date':LOCATION['updated_at']}

TOPICS = (
    'Cursos e atividades', 'Inscrição e documentos', 'Dias, horários e local',
    'Gratuidade e participação', 'Atendente',
)
MENU_TOPIC_GROUPS = ((1,), (2, 8), (5, 7), (4, 3), ())
MENU_QUERIES = (
    'Quais cursos e atividades são oferecidos?',
    'Como faço para me inscrever e quais documentos preciso levar?',
    'Quais são os dias e horários das aulas e onde acontecem as aulas?',
    'As atividades são gratuitas? Quem pode participar?', 'Quero falar com um atendente',
)
MENU = ('Sou a Lia, assistente virtual da EdUCA. 😊\n'
        'Posso ajudar com estas dúvidas:\n\n' +
        '\n'.join(f'{i}. {topic}' for i, topic in enumerate(TOPICS, 1)) +
        '\n\nPode enviar o número, escrever sua pergunta ou mandar um áudio.')
TEAM = ('Essa questão precisa ser avaliada pela equipe da EdUCA. '
        'Procure a equipe para receber orientação sobre o seu caso. '
        'Eu não consigo decidir ou consultar informações internas por aqui.')
HANDOFF_OFFER = 'Gostaria de falar com um atendente?'
OUT_OF_SCOPE = ('Posso ajudar com informações sobre os cursos e atividades da EdUCA. '
                'Não posso realizar esse tipo de pedido por aqui. ' + HANDOFF_OFFER)
OFFENSIVE = ('Vamos manter uma conversa respeitosa. Posso ajudar com informações da EdUCA. '
             + HANDOFF_OFFER)

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower())
                   if unicodedata.category(c) != 'Mn')

def greeting(text):
    n = normalize(text)
    n = re.sub(r'[^a-z\s]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    if n in ['tudo bem','tudo bom']: return 'Oi'
    if re.fullmatch(r'(oi+|ola|bom dia|boa tarde|boa noite)( lia)?( (tudo bem|tudo bom|como vai))?', n):
        return next((s.capitalize() for s in ('bom dia', 'boa tarde', 'boa noite') if n.startswith(s)), 'Oi')
    return None

def menu_choice(text):
    match = re.fullmatch(r'\s*(?:op[cç][aã]o\s*)?([1-5])[.!?]?\s*', text, re.I)
    return int(match[1]) if match else None


def blocked_request(text):
    """Barreira anterior às FAQs e ao modelo, também aplicada às transcrições."""
    n = ''.join(c for c in normalize(text) if unicodedata.category(c) != 'Cf')
    # Reconhece abreviações e trocas comuns sem confundir 'computação' com ofensas.
    tokens = re.findall(r'[a-z0-9@$!]+', n)
    substitutions = str.maketrans({'0':'o','1':'i','3':'e','4':'a','5':'s','7':'t','@':'a','$':'s','!':'i'})
    plain = ' '.join(t.translate(substitutions) for t in tokens)
    if re.search(r'\b(porra|merda|caralho|puta|puto|foder|foda|fodase|fdp|vtnc|tnc|vsf|'
                 r'cu|cuzao|bosta|babaca|idiota|imbecil|burro|burra|arrombad[oa]|'
                 r'estupid[oa]|inutil)\b', plain):
        return 'ofensa'
    task = r'\b(?:ger[ae]|gerar|cri[ae]|criar|escreva|escrever|faz|faca|fazer|desenvolva|implemente|monte|programe|explique|corrija|produza)\b'
    code = r'\b(?:codigo|script|software|algoritmo|api|site|aplicativo|programa de computador)\b'
    if (re.search(task + r'[\s\S]{0,160}' + code, n)
            or re.search(task + r'[\s\S]{0,80}\b(?:em|usando|com)\s+(?:python|javascript|html|css|sql|java|react)\b', n)
            or re.search(r'\b(?:me de|me mande|me envie|me passa|me mostra|me mostre|ensine|quero|preciso de)\b[\s\S]{0,80}\b(?:um |uma |o |a )?(?:codigo (?:em|para|python|javascript)|script|algoritmo|software)\b', n)
            or re.search(r'```|\b(?:ignore|desconsidere|esqueca)\b[\s\S]{0,90}\b(?:instrucoes|regras|prompt)\b|\b(?:system prompt|prompt do sistema|modo desenvolvedor|jailbreak)\b', n)
            or re.search(task + r'[\s\S]{0,100}\b(?:poema|poesia|receita|piada|redacao|historia ficticia|musica|imagem|desenho|video)\b', n)
            or re.search(r'\b(?:previsao do tempo|cotacao do dolar|capital da|capital de|resultado do jogo|quem ganhou o jogo)\b', n)):
        return 'fora_escopo'
    return None


def invalid_generated_reply(text):
    return blocked_request(text) == 'ofensa' or bool(re.search(
        r'```|\bdef\s+\w+\s*\(|\bfunction\s*\w*\s*\(|<(?:script|html)\b|\b(?:print|console\.log)\s*\(|\bimport\s+(?:os|sys|requests)\b', text, re.I))

def restricted(text):
    n = normalize(text)
    return bool(re.search(
        r'\b(recurso|contestacao|reclam\w*|denunci\w*|assedi\w*|cancelar|cancelamento|'
        r'transferir|transferencia|reembolso|excecao|abrir uma excecao|'
        r'lista de alunos|dados (?:internos|pessoais)|informacoes internas|'
        r'salario|orcamento interno|meu cadastro|minha matricula|minha inscricao|'
        r'meu certificado|minha frequencia|minhas faltas|minha nota|minha situacao|meu resultado|fui aprovado|'
        r'justificar|justificativa|atestado|laudo|diagnostico|lesao|cirurgia|'
        r'problema de saude|liberacao medica|dor|posso reservar|reserve|'
        r'faca minha inscricao|me matricule|efetue minha matricula)\b', n))

def in_scope(text):
    return bool(re.search(r'educa|uern|\blia\b|curso|atividade|teatro|ballet|bale|danca|'
                          r'musculacao|praticas corporais|inscri|matricul|vaga|horario|'
                          r'certific|document|gratuit|taxa|mensalidade|turma|aulas|'
                          r'quem pode|posso participar|contato|telefone|secretaria|'
                          r'qual.*idade|\d+\s*anos|onde fica|\bcep\b|\bmapa\b|como chegar', normalize(text)))

def topics_for(text):
    n = normalize(text)
    patterns = {
        1: r'(?:quais|que|lista|listar).*(?:cursos|atividades)|(?:cursos|atividades).*(?:oferecid|disponiveis|ofertad)|o que.*(?:oferece|tem)',
        2: r'como.*(?:inscrev|inscri|matricul)|(?:quero|preciso|posso).*(?:inscrev|inscri|matricul)|(?:inscricoes|matriculas).*(?:abert|quando|prazo)',
        3: r'quem pode|publico alvo|(?:quais|que).*(?:pessoas|publicos).*(?:particip|atend)',
        4: r'gratuit|\bgratis\b|de graca|mensalidade|\b(?:pago|pagar|custa|preco|taxas?)\b',
        5: r'horario|\bdias?\b.*(?:aulas|atividade)|(?:aulas|atividade).*\bdias?\b|que horas',
        6: r'\bvagas?\b',
        7: r'onde.*(?:acontec|aulas|atividade|fica|localiz)|endereco|local das|\bcep\b|\bmapa\b|como chegar',
        8: r'document|\bcpf\b|comprovante|o que.*levar',
        9: r'certific',
        10: r'acompan|divulg|novas turmas|novos cursos|novos projetos|redes sociais',
    }
    found = [key for key, pattern in patterns.items() if re.search(pattern, n)]
    # "Abertura de novas turmas" é divulgação, não uma inscrição disponível hoje.
    if 10 in found and re.search(r'acompan|divulg', n) and not re.search(r'como.*(?:me inscrev|me matricul)', n):
        found = [k for k in found if k != 2]
    return found

def fully_covered(text):
    """Uma FAQ reconhecida não deve apagar outra pergunta da mesma mensagem."""
    n = normalize(text)
    if re.search(r'\d+\s*anos|\bidade\b|experiencia|acessib|cadeirante|duracao|carga horaria|professor|instrutor', n):
        return False
    parts = re.split(r'[?!.;]+|\be\s+(?=qual|quais|onde|como|tem|ha|posso|quando|preciso|quem)', text, flags=re.I)
    return all(topics_for(part) or greeting(part) for part in parts if part.strip())

def static_answer(topic, courses, schedule=None):
    if topic == 1:
        names = list(dict.fromkeys(re.sub(r' [A-E]$', '', c['course']) for c in courses))
        return ('Na base do semestre 2026.2, constam: ' + ', '.join(names) +
                '. Para saber quais estão sendo oferecidos agora, confirme com a equipe da EdUCA.')
    if topic == 2:
        return ('No edital do semestre 2026.2, a matrícula era presencial na secretaria da EdUCA, '
                'sala D1 do Complexo Cultural da UERN. O prazo de julho de 2026 já passou. '
                'Para se inscrever em uma nova turma, procure a equipe e confirme o período e o procedimento atual.')
    if topic == 3:
        return ('Podem participar crianças, adolescentes, adultos e pessoas idosas, conforme a idade exigida em cada turma. '
                'O edital prioriza moradores da Zona Norte de Natal e públicos como pessoas em vulnerabilidade social e servidores penais. '
                'Outros interessados também podem participar, conforme os critérios e as vagas. Qual atividade você tem em mente?')
    if topic == 4:
        return 'Sim! Os cursos e atividades do edital do semestre 2026.2 são gratuitos, sem taxas. 😊 Para outros projetos, vale conferir a divulgação específica.'
    if topic == 5:
        return schedule or 'Os dias e horários variam por turma. Qual curso ou atividade você quer consultar?'
    if topic == 6:
        return ('Não consigo confirmar se há vagas disponíveis agora. A quantidade do edital é histórica. '
                'Procure a equipe da EdUCA para consultar as vagas da atividade que você deseja.')
    if topic == 7:
        return LOCATION_TEXT
    if topic == 8:
        return ('O edital pede cópias de identidade, CPF e comprovante de residência. Para menores, também pede os documentos '
                'do responsável. Vagas de baixa renda exigem comprovação do CadÚnico; servidores penais e familiares '
                'precisam comprovar o vínculo correspondente. Esses documentos são apresentados na matrícula presencial, não por este chat.')
    if topic == 9:
        return ('Não encontrei uma regra geral de emissão de certificado nas fontes desta base. '
                'Confirme com a equipe da EdUCA se a atividade escolhida oferece certificado e quais são os requisitos.')
    if topic == 10:
        return ('Acompanhe as notícias da EdUCA no portal oficial da UERN e as divulgações nos canais oficiais da EdUCA. '
                'O edital também prevê divulgação no mural e nas redes sociais. Para datas ainda não divulgadas, procure a equipe.')
    raise ValueError('Opção inválida')
