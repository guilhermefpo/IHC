"""Filtro de perguntas: remove "enrolação" e barra o que não é sobre o estoque.

Roda antes do LLM, em menos de 1 ms. Saudações, agradecimentos, pedidos de
alteração, pedidos que o bot não atende, ofensas e perguntas fora do tema
recebem resposta imediata, sem gastar uma chamada ao modelo.
"""

import difflib
import re
import unicodedata

# ---------------------------------------------------------------------------
# Expressões removidas da pergunta (sempre frases completas, nunca palavras
# soltas como "tem", para não cortar parte da pergunta)
# ---------------------------------------------------------------------------
_AGRADECIMENTOS = r"muito obrigad[oa]|obrigad[oa]|obg|valeu|vlw|grat[oa]|agrade[cç]o"
_SAUDACOES = (
    r"bom dia|boa tarde|boa noite|ol[aá]|oi+e?|e a[ií]|eae|salve|opa|hey|hello|"
    r"tudo bem|tudo bom|tudo certo|como vai( voc[eê])?"
)
_CONFIRMACOES = r"ok|okay|certo|entendi|show|perfeito|t[aá] bom|t[aá] bem|beleza|blz|legal"

_EXPRESSOES = [
    _SAUDACOES,
    # Cortesias, agradecimentos e confirmações.
    r"por favor|por gentileza|pfv?|com licen[cç]a|desculpa( (o|por) incomodar)?",
    _AGRADECIMENTOS,
    _CONFIRMACOES,
    # Rodeios antes da pergunta de fato.
    r"(eu )?(queria|gostaria de|quero|preciso|precisava) "
    r"(saber|perguntar|ver|consultar|checar|conferir)( se)?",
    r"(eu )?(queria|gostaria|quero) que (voc[eê]|vc) (me )?"
    r"(fizesse|fa[cç]a|calculasse|calcule|mostrasse|mostre|dissesse|diga|informasse|informe)",
    r"(voc[eê]|vc) (pode|poderia|consegue|conseguiria|saberia)( me)? "
    r"(dizer|falar|informar|responder|mostrar|ver|ajudar|calcular|fazer)( se)?",
    r"(sabe|saberia) (me )?(dizer|informar)( se)?",
    r"ser[aá] que",
    r"tem como (me )?(dizer|saber|ver|informar|mostrar|consultar)( se)?",
    r"me (diz|diga|fala|fale|informa|informe|mostra|mostre|ajuda|ajude)( a)?( se)?",
    r"(eu )?(tenho|tenho uma|tô com uma|to com uma|estou com uma) d[uú]vida",
    r"(s[oó] )?(uma )?(d[uú]vida|pergunta|coisinha|coisa)( r[aá]pida)?",
]
_PADRAO_EXPRESSOES = re.compile(
    r"\b(" + "|".join(f"(?:{e})" for e in _EXPRESSOES) + r")\b",
    re.IGNORECASE,
)
_PADRAO_AGRADECIMENTO = re.compile(rf"\b({_AGRADECIMENTOS})\b", re.IGNORECASE)
_PADRAO_SAUDACAO = re.compile(rf"\b({_SAUDACOES})\b", re.IGNORECASE)
_PADRAO_CONFIRMACAO = re.compile(rf"\b({_CONFIRMACOES})\b", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Pedidos que o bot não atende (checados antes da relevância, pois costumam
# citar termos do estoque, ex.: "altere o preço do arroz")
# ---------------------------------------------------------------------------
_PADRAO_ALTERACAO = re.compile(
    r"\b(alter[ea]|mud[ea]|apag(a|ue)|delet[ea]|exclu[ai]|remov[ae]|cadastr[ea]|"
    r"adicion[ea]|insir[ae]|atualiz[ea]|zer[ea]|coloca|coloque|troca|troque|edit[ea]|"
    r"aument[ea]|diminu[ai]|reduz[ae])\b",
    re.IGNORECASE,
)
_PADRAO_NAO_SUPORTADO = re.compile(
    r"\b(mapa mental|gr[aá]fico|planilha|relat[oó]rio|desenh[ea]|imagem|pdf|"
    r"excel|apresenta[cç][aã]o|slides?|diagrama)\b",
    re.IGNORECASE,
)
# Saúde: o estoque não tem remédios e o bot não deve dar orientação médica.
_PADRAO_SAUDE = re.compile(
    r"\b(rem[eé]dios?|medicamentos?|medica[cç][aã]o|doen[cç]as?|doentes?|"
    r"passando mal|sintomas?|febre|dor de|curar|cura|tratamento|"
    r"m[eé]dic[oa]s?|hospital|receita m[eé]dica)\b",
    re.IGNORECASE,
)
# Lista curta de ofensas comuns; só vale quando a mensagem não é sobre o estoque.
_PADRAO_OFENSA = re.compile(
    r"\b(vai tomar|vtnc|tnc|fdp|filho da puta|porra|caralho|merda|idiota|"
    r"burr[oa]|est[uú]pid[oa]|lixo|bosta|ot[aá]ri[oa]|imbecil|desgra[cç]a|cu)\b",
    re.IGNORECASE,
)

# Marcadores de uma segunda pergunta na mesma mensagem.
_PADRAO_PROXIMA_PARTE = re.compile(
    r"[,.;]?\s*\b(a[ií] depois|e depois|depois disso|em seguida|"
    r"e tamb[eé]m|tamb[eé]m quero|e agora)\b"
    # Pedido dirigido ao bot logo depois do marcador ("... você faça o de X").
    r"(\s+(voc[eê]|vc)\s+(fa[cç]a|fizesse|calcule|mostre|diga|veja))?",
    re.IGNORECASE,
)

# Sinônimos trocados antes do LLM: o modelo pequeno ignorou essa regra no
# prompt e filtrou departamento = 'legumes' AND departamento = 'frutas'.
_SINONIMOS_DEPARTAMENTO = (
    (
        re.compile(
            r"\b(frutas|legumes|verduras|hortifr[uú]ti)"
            r"((\s*,\s*|\s+e\s+)(frutas|legumes|verduras))*\b",
            re.IGNORECASE,
        ),
        "hortifruti",
    ),
    (re.compile(r"\bmaterial escolar\b", re.IGNORECASE), "papelaria"),
)

# ---------------------------------------------------------------------------
# Filtros do SQL, usados para dar contexto à resposta e sugerir nomes
# ---------------------------------------------------------------------------
PADRAO_PRODUTO = re.compile(
    r"nome\)?\s*(?:=|like)\s*(?:lower\()?\s*'%?([^'%]+)%?'",
    re.IGNORECASE,
)
PADRAO_DEPARTAMENTO = re.compile(
    r"departamento\)?\s*(?:=|like)\s*(?:lower\()?\s*'%?([^'%]+)%?'",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Vocabulário do domínio (sem acento). Nomes de produtos e departamentos
# vêm do banco (ver fatec.carregar_vocabulario) e se somam a estes termos.
# ---------------------------------------------------------------------------
PALAVRAS_DOMINIO = frozenset("""
    preco precos custa custam custo custos valor valores caro cara caros caras
    barato barata baratos baratas estoque estoques quantidade quantidades
    unidade unidades resta restam sobrou sobraram sobra disponivel disponiveis
    acabou acabando falta faltando vencido vencidos vencida vencidas vence
    vencem venceu vencimento vencimentos validade valido validos fabricado
    fabricados fabricada fabricadas fabricacao departamento departamentos
    categoria categorias setor setores produto produtos item itens mercadoria
    mercadorias total soma media maior menor ativo ativos inativo inativos
    cadastrado cadastrados cadastro tipo tipos descricao peso quilo quilos kg
    grama gramas litro litros tamanho embalagem frutas legumes verduras
""".split())

# Fração da mensagem descartada a partir da qual o bot dá a dica de perguntar
# de forma direta. Mensagens curtas nunca recebem a dica.
LIMITE_ENROLACAO = 0.5
_MINIMO_PALAVRAS_ENROLACAO = 12

# Palavras curtas demais geram falsos positivos na comparação aproximada.
_TAMANHO_MINIMO_APROXIMADO = 5
_SIMILARIDADE_MINIMA = 0.8
# Palavras comuns parecidas com termos do estoque que nunca devem casar por
# aproximação (vistas nos logs: "estou" ~ "estoque", "preciso" ~ "preço").
_PALAVRAS_COMUNS = frozenset("""
    estou esta estava estamos estao estar estive preciso precisa precisava
    precisamos preso presa prezo preza pessoa cabo sobre
""".split())

MENSAGENS = {
    "saudacao": (
        "Olá! Sou o assistente do estoque. Pergunte, por exemplo: "
        "quanto custa o arroz? ou quais produtos estão vencidos?"
    ),
    "agradecimento": "Por nada! Se precisar, é só perguntar sobre o estoque.",
    "confirmacao": "Combinado! Se precisar de algo do estoque, é só perguntar.",
    "fora_do_escopo": (
        "Só consigo responder perguntas sobre o estoque (preços, "
        "quantidades, validade e departamentos). Exemplo: "
        "quanto tem de feijão?"
    ),
    "alteracao": (
        "Eu só consulto o estoque; não altero, cadastro nem apago dados. "
        "Posso, por exemplo, mostrar os produtos inativos ou o preço de um item."
    ),
    "nao_suportado": (
        "Não consigo gerar gráficos, mapas mentais, relatórios ou arquivos. "
        "Posso responder perguntas como: qual o preço médio por departamento? "
        "ou quais produtos vencem este mês?"
    ),
    "saude": (
        "Sinto muito que você não esteja bem. Não tenho remédios no estoque "
        "e não posso dar orientação de saúde. Se estiver passando mal, procure "
        "um médico ou ligue 192 (SAMU). Para produtos do estoque, é só perguntar."
    ),
    "ofensa": (
        "Vamos manter o respeito. Posso ajudar com preços, quantidades "
        "e validade dos produtos."
    ),
}


# ---------------------------------------------------------------------------
# Funções
# ---------------------------------------------------------------------------
def sem_acento(texto: str) -> str:
    """
    Remove acentos para comparar palavras ("feijão" == "feijao").
    """
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def _arrumar(texto: str) -> str:
    """
    Junta espaços e tira a pontuação que sobrou nas bordas.
    """
    texto = re.sub(r"\s*([,;.!?])(\s*[,;.!?])+", r"\1", texto)
    return " ".join(texto.split()).strip(" ,;.!?:-")


def limpar_pergunta(texto: str) -> str:
    """
    Remove saudações, cortesias e rodeios, mantendo os acentos da pergunta
    (o SQL compara nomes com acento, ex.: 'feijão').
    """
    return _arrumar(_PADRAO_EXPRESSOES.sub(" ", texto.lower()))


def eh_do_dominio(texto: str, vocabulario: frozenset = frozenset()) -> bool:
    """
    Indica se o texto tem algum termo do estoque, tolerando erros de digitação.
    """
    texto = sem_acento(texto.lower())
    termos = PALAVRAS_DOMINIO | vocabulario

    # Nomes compostos ("creme dental", "papel-higiênico") são buscados inteiros.
    if any(" " in t or "-" in t for t in termos if t in texto):
        return True

    for palavra in re.findall(r"[\w-]+", texto):
        if palavra in termos:
            return True
        if palavra in _PALAVRAS_COMUNS:
            continue
        if len(palavra) >= _TAMANHO_MINIMO_APROXIMADO and difflib.get_close_matches(
            palavra, termos, n=1, cutoff=_SIMILARIDADE_MINIMA
        ):
            return True
    return False


def separar_partes(texto: str):
    """
    Separa a primeira pergunta de uma segunda ("... e depois faça o de X").

    Returns:
        Tupla (primeira_parte, resto); resto é "" quando há uma só pergunta.
    """
    partes = _PADRAO_PROXIMA_PARTE.split(texto, maxsplit=1)
    if len(partes) == 1:
        return texto, ""
    return _arrumar(partes[0]), _arrumar(partes[-1])


def avaliar_pergunta(texto: str, vocabulario: frozenset = frozenset()):
    """
    Classifica a pergunta antes de enviá-la ao LLM.

    Frases sem nenhum termo do estoque (ex.: o nome do bot ou "eu sou
    Fulano") são descartadas e só as frases relevantes seguem adiante.

    Returns:
        Tupla (status, texto_limpo). O status é "ok" ou uma das chaves de
        MENSAGENS.
    """
    limpo = limpar_pergunta(texto)
    if not limpo:
        if _PADRAO_AGRADECIMENTO.search(texto):
            return "agradecimento", limpo
        if _PADRAO_SAUDACAO.search(texto):
            return "saudacao", limpo
        return "confirmacao", limpo

    if _PADRAO_ALTERACAO.search(limpo):
        return "alteracao", limpo
    if _PADRAO_SAUDE.search(limpo):
        return "saude", limpo
    if _PADRAO_NAO_SUPORTADO.search(limpo):
        return "nao_suportado", limpo

    frases = [_arrumar(f) for f in re.split(r"(?<=[.!?])\s+", limpo)]
    relevantes = [f for f in frases if f and eh_do_dominio(f, vocabulario)]
    if not relevantes:
        if _PADRAO_OFENSA.search(limpo):
            return "ofensa", limpo
        return "fora_do_escopo", limpo
    pergunta = ". ".join(relevantes)
    for padrao, departamento in _SINONIMOS_DEPARTAMENTO:
        pergunta = padrao.sub(departamento, pergunta)
    return "ok", pergunta


def tem_enrolacao(texto: str, pergunta: str) -> bool:
    """
    Indica se a maior parte da mensagem foi descartada por não ter relação
    com o estoque (ex.: uma história de jogo com a pergunta no final).

    Saudações e cortesias não contam: "bom dia, quanto custa o arroz?" é
    uma pergunta natural, não enrolação.
    """
    total = len(limpar_pergunta(texto).split())
    if total < _MINIMO_PALAVRAS_ENROLACAO:
        return False
    aproveitadas = len(pergunta.split())
    return (total - aproveitadas) / total > LIMITE_ENROLACAO
