"""Núcleo Text-to-SQL: transforma perguntas em português em SQL e executa no SQLite.

Fluxo: generate() -> cache -> LLM local (Jan/Qwen3 via DSPy) -> validação -> consulta.
"""

import difflib
import re
import sqlite3
import dspy
import os
import json
from contextvars import ContextVar
from contextlib import closing
from time import perf_counter
from functools import lru_cache
from dotenv import load_dotenv
from timing import measure
from filtro import (
    MENSAGENS,
    PADRAO_PRODUTO,
    avaliar_pergunta,
    sem_acento,
    separar_partes,
    tem_enrolacao,
)

# ---------------------------------------------------------------------------
# Configuração geral: variáveis de ambiente, métricas e caminho do banco
# ---------------------------------------------------------------------------
load_dotenv()

request_metrics = ContextVar("request_metrics", default=None)

# Evita respostas enormes que viram várias mensagens no Telegram.
LIMITE_LINHAS = 50

# Nomes de produtos e departamentos usados pelo filtro; preenchido no create_db().
VOCABULARIO_DB = frozenset()
# Nomes originais (com acento) para sugerir quando um produto não é achado.
PRODUTOS_DB = ()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "lojas.db")


# ---------------------------------------------------------------------------
# Banco de dados: cria a tabela produtos e insere dados de exemplo
# ---------------------------------------------------------------------------
def create_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY,
            nome TEXT,
            departamento TEXT,
            produto TEXT,
            preco REAL,
            qntd INTEGER,
            data_fabri DATE,
            data_venci DATE,
            status BOOLEAN
        );
    """)

    c.execute("SELECT COUNT(*) FROM produtos")
    count = c.fetchone()[0]

    if count == 0:
        c.execute("""
            INSERT INTO produtos VALUES
            (1, 'sabonete', 'higiene', 'Produto de higiene pessoal', 12.90, 300, '2025-10-13', '2027-09-10', TRUE),
            (2, 'água', 'bebidas', 'Garrafa de água mineral', 67.67, 15, '2026-05-03', '2027-05-03', TRUE),
            (3, 'coca-cola', 'bebidas', 'Refrigerante de cola 2L', 10.40, 700, '2026-06-09', '2027-12-12', TRUE),
            (4, 'notebook', 'eletrônicos', 'Notebook 15 polegadas', 3499.90, 25, '2026-01-15', '2030-01-15', TRUE),
            (5, 'shampoo', 'higiene', 'Shampoo para cabelos', 18.50, 150, '2026-02-10', '2028-02-10', TRUE),
            (6, 'condicionador', 'higiene', 'Condicionador para cabelos', 19.90, 120, '2026-02-12', '2028-02-12', TRUE),
            (7, 'arroz', 'alimentos', 'Arroz branco 5kg', 29.99, 200, '2026-03-01', '2027-03-01', TRUE),
            (8, 'feijão', 'alimentos', 'Feijão carioca 1kg', 8.99, 350, '2026-03-05', '2027-03-05', TRUE),
            (9, 'macarrão', 'alimentos', 'Macarrão espaguete 500g', 5.49, 400, '2026-03-10', '2028-03-10', TRUE),
            (10, 'açúcar', 'alimentos', 'Açúcar refinado 1kg', 4.99, 280, '2026-04-01', '2028-04-01', TRUE),
            (11, 'café', 'alimentos', 'Café torrado e moído 500g', 18.90, 180, '2026-04-05', '2027-10-05', TRUE),
            (12, 'leite', 'bebidas', 'Leite integral 1L', 5.99, 500, '2026-08-01', '2026-09-01', TRUE),
            (13, 'suco', 'bebidas', 'Suco de laranja 1L', 7.50, 220, '2026-07-10', '2027-01-10', TRUE),
            (14, 'bolacha', 'alimentos', 'Biscoito recheado 140g', 3.99, 450, '2026-05-15', '2027-05-15', TRUE),
            (15, 'chocolate', 'alimentos', 'Chocolate ao leite 90g', 6.99, 300, '2026-06-20', '2027-06-20', TRUE),
            (16, 'detergente', 'limpeza', 'Detergente líquido 500ml', 2.99, 600, '2026-01-20', '2028-01-20', TRUE),
            (17, 'sabão', 'limpeza', 'Sabão em pó 1kg', 14.90, 250, '2026-02-15', '2028-02-15', TRUE),
            (18, 'amaciante', 'limpeza', 'Amaciante de roupas 2L', 16.90, 180, '2026-03-20', '2028-03-20', TRUE),
            (19, 'desinfetante', 'limpeza', 'Desinfetante 2L', 9.90, 320, '2026-04-10', '2028-04-10', TRUE),
            (20, 'esponja', 'limpeza', 'Esponja multiuso', 3.50, 700, '2026-05-01', '2030-05-01', TRUE),
            (21, 'papel-higiênico', 'higiene', 'Papel higiênico pacote 12 unidades', 19.99, 250, '2026-01-05', '2030-01-05', TRUE),
            (22, 'creme dental', 'higiene', 'Creme dental 90g', 7.99, 300, '2026-02-01', '2028-02-01', TRUE),
            (23, 'escova dental', 'higiene', 'Escova de dentes', 8.50, 200, '2026-03-01', '2030-03-01', TRUE),
            (24, 'desodorante', 'higiene', 'Desodorante aerosol 150ml', 13.90, 180, '2026-04-15', '2028-04-15', TRUE),
            (25, 'papel-toalha', 'limpeza', 'Papel toalha 2 rolos', 7.90, 230, '2026-05-10', '2030-05-10', TRUE),
            (26, 'celular', 'eletrônicos', 'Smartphone 128GB', 1899.90, 40, '2026-01-10', '2030-01-10', TRUE),
            (27, 'tablet', 'eletrônicos', 'Tablet 10 polegadas', 1299.90, 30, '2026-02-20', '2030-02-20', TRUE),
            (28, 'monitor', 'eletrônicos', 'Monitor LED 24 polegadas', 899.90, 35, '2026-03-15', '2030-03-15', TRUE),
            (29, 'teclado', 'eletrônicos', 'Teclado USB', 89.90, 100, '2026-04-20', '2030-04-20', TRUE),
            (30, 'mouse', 'eletrônicos', 'Mouse óptico USB', 59.90, 150, '2026-05-20', '2030-05-20', TRUE),
            (31, 'fones', 'eletrônicos', 'Fone de ouvido Bluetooth', 149.90, 80, '2026-06-01', '2030-06-01', TRUE),
            (32, 'carregador', 'eletrônicos', 'Carregador USB-C', 79.90, 120, '2026-06-10', '2030-06-10', TRUE),
            (33, 'caderno', 'papelaria', 'Caderno universitário 200 folhas', 24.90, 100, '2026-01-25', '2030-01-25', TRUE),
            (34, 'caneta', 'papelaria', 'Caneta esferográfica azul', 2.50, 500, '2026-02-05', '2030-02-05', TRUE),
            (35, 'lápis', 'papelaria', 'Lápis preto HB', 1.99, 600, '2026-03-05', '2030-03-05', TRUE),
            (36, 'borracha', 'papelaria', 'Borracha branca escolar', 1.50, 450, '2026-04-05', '2030-04-05', TRUE),
            (37, 'mochila', 'papelaria', 'Mochila escolar', 129.90, 60, '2026-05-05', '2030-05-05', TRUE),
            (38, 'carne', 'alimentos', 'Carne bovina 1kg', 39.90, 100, '2026-08-05', '2026-08-20', TRUE),
            (39, 'frango', 'alimentos', 'Peito de frango 1kg', 16.90, 120, '2026-08-06', '2026-08-21', TRUE),
            (40, 'queijo', 'alimentos', 'Queijo muçarela 500g', 24.90, 90, '2026-08-07', '2026-09-07', TRUE),
            (41, 'manteiga', 'alimentos', 'Manteiga 200g', 12.90, 110, '2026-07-15', '2026-10-15', TRUE),
            (42, 'iogurte', 'alimentos', 'Iogurte natural 170g', 4.50, 200, '2026-08-08', '2026-08-25', TRUE),
            (43, 'maçã', 'hortifruti', 'Maçã nacional 1kg', 9.90, 150, '2026-08-10', '2026-08-20', TRUE),
            (44, 'banana', 'hortifruti', 'Banana prata 1kg', 6.90, 180, '2026-08-10', '2026-08-18', TRUE),
            (45, 'laranja', 'hortifruti', 'Laranja 1kg', 5.90, 200, '2026-08-09', '2026-08-19', TRUE),
            (46, 'batata', 'hortifruti', 'Batata inglesa 1kg', 7.90, 170, '2026-08-09', '2026-08-25', TRUE),
            (47, 'tomate', 'hortifruti', 'Tomate 1kg', 8.90, 130, '2026-08-11', '2026-08-18', TRUE),
            (48, 'cebola', 'hortifruti', 'Cebola 1kg', 6.50, 140, '2026-08-11', '2026-08-25', TRUE),
            (49, 'azeite', 'alimentos', 'Azeite de oliva 500ml', 32.90, 75, '2026-01-15', '2028-01-15', TRUE),
            (50, 'farinha', 'alimentos', 'Farinha de trigo 1kg', 5.90, 250, '2026-05-15', '2027-11-15', TRUE)
        """)

    conn.commit()
    conn.close()

    carregar_vocabulario()


def carregar_vocabulario():
    """
    Lê nomes de produtos e departamentos do banco para o filtro de perguntas.
    Assim, um produto cadastrado no futuro já é reconhecido sem mudar código.
    """
    global VOCABULARIO_DB, PRODUTOS_DB
    with closing(sqlite3.connect(db_path)) as conn:
        linhas = conn.execute("SELECT nome, departamento FROM produtos").fetchall()
    VOCABULARIO_DB = frozenset(
        sem_acento(str(valor).lower())
        for linha in linhas
        for valor in linha
        if valor
    )
    PRODUTOS_DB = tuple(sorted({str(nome) for nome, _ in linhas if nome}))


def sugerir_produtos(termo: str, limite: int = 3) -> list:
    """
    Sugere produtos com nome parecido ("feijão carioca" -> ["feijão"]).
    """
    termo_comparavel = sem_acento(termo.lower())
    nomes = {sem_acento(nome.lower()): nome for nome in PRODUTOS_DB}
    # Nome cadastrado contido no termo buscado (ou o contrário).
    contidos = [
        original for comparavel, original in nomes.items()
        if re.search(rf"\b{re.escape(comparavel)}\b", termo_comparavel)
        or re.search(rf"\b{re.escape(termo_comparavel)}\b", comparavel)
    ]
    parecidos = [
        nomes[n] for n in difflib.get_close_matches(
            termo_comparavel, nomes, n=limite, cutoff=0.6
        )
    ]
    return list(dict.fromkeys(contidos + parecidos))[:limite]


# ---------------------------------------------------------------------------
# Schema enviado ao LLM e usado na validação do SQL
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE produtos (
    id INTEGER PRIMARY KEY,
    nome TEXT,
    departamento TEXT,
    produto TEXT,
    preco REAL,
    qntd INTEGER,
    data_fabri DATE,
    data_venci DATE,
    status BOOLEAN
);
"""

# ---------------------------------------------------------------------------
# Modelo de linguagem: conexão com o Jan e parâmetros de geração
# ---------------------------------------------------------------------------
lm = dspy.LM(
    # Troque JAN_MODEL no .env ao trocar o modelo no Jan (ex.: versão Q8_0).
    f"openai/{os.getenv('JAN_MODEL', 'Qwen3-0_6B-BF16')}",
    api_base=os.getenv("JAN_API_BASE", "http://127.0.0.1:1337/v1"),
    api_key="not-needed",
    temperature=0.0,
    # O SQL mais longo observado teve 78 tokens; 200 cabe com folga no slot.
    max_tokens=200,
    # Para a geração no marcador final do DSPy, sem tokens extras.
    stop=["[[ ## completed ## ]]"],
    # Desliga o raciocínio do Qwen3; ele era ~90% do tempo de resposta.
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)

# Sem o fallback para JSONAdapter, uma falha de parse não vira uma 2ª chamada.
dspy.configure(lm=lm, adapter=dspy.ChatAdapter(use_json_adapter_fallback=False))


# ---------------------------------------------------------------------------
# Prompt (assinatura DSPy): regras e exemplos de pergunta -> SQL
# ---------------------------------------------------------------------------
class TextToSQL(dspy.Signature):
    """
    Interprete o significado da pergunta em português e transforme-a
    em uma consulta SQLite.

    Não procure apenas frases idênticas aos exemplos. Entenda sinônimos,
    variações, erros simples de escrita e formas informais de perguntar.

    BANCO DISPONÍVEL:

    Tabela produtos:

    - id: identificador do produto
    - nome: nome do produto
    - departamento: categoria ou setor
    - produto: descrição do produto
    - preco: preço de uma unidade
    - qntd: quantidade de unidades disponíveis no estoque
    - data_fabri: data de fabricação
    - data_venci: data de vencimento
    - status: TRUE significa ativo e FALSE significa inativo

    INTERPRETAÇÃO DE LINGUAGEM NATURAL:

    Expressões relacionadas à quantidade disponível:

    - quanto tem
    - quanto ainda tem
    - quanto resta
    - quanto sobrou
    - quantidade disponível
    - unidades disponíveis
    - estoque de um produto

    Todas essas expressões significam consultar a coluna qntd.

    CONTAGEM E AMBIGUIDADE:
    - Produtos diferentes, tipos de produtos ou quantidade de cadastros: COUNT(*).
    - Total de unidades, soma das quantidades: SUM(qntd).
    - Quantidade de um produto identificado: qntd, filtrando por nome.
    - "Quantos produtos há no estoque?" sem distinguir tipos de unidades:
      retorne ESCLARECER: Você quer contar os produtos diferentes ou somar
      as unidades disponíveis? Reenvie a pergunta completa com essa informação.
    - Não invente filtros de ativo, disponibilidade ou departamento que não
      foram pedidos. Para disponibilidade, use qntd > 0 e status = TRUE.

    DATAS E INFORMAÇÕES AUSENTES:
    - Fabricação corresponde somente a data_fabri; vencimento e validade
      correspondem somente a data_venci. Nunca troque esses significados.
    - Não existe data de cadastro, entrada, compra ou histórico de preços.
      Se a pergunta depender desses dados, retorne SEM_DADOS: seguido de
      uma explicação curta do campo ausente. Nunca substitua por outra data.
    - "Cadastrados em janeiro" exige data de cadastro, que não existe.
      "Produtos cadastrados" sem filtro temporal pode se referir aos registros.
    - Se mencionar janeiro ou outro mês sem ano, peça o ano com ESCLARECER:.
      Se disser "deste ano", use o ano atual do SQLite.
    - Se faltar o significado da data (fabricação ou vencimento), peça essa
      informação com ESCLARECER:. Nunca escolha uma coluna arbitrariamente.
    - Datas literais devem usar YYYY-MM-DD. Nunca use DATE('janeiro').
    - "Entre 2026-01-01 e 2026-01-31" inclui os dois dias: use >= '2026-01-01'
      e < '2026-02-01'. Preserve os limites inclusivos ou exclusivos pedidos.
    - Média de preços é AVG(preco); média ponderada por unidades somente
      quando solicitada. Preço atual é preco; não há histórico de preços.
    - Cada mensagem é independente. Ao esclarecer, peça que a pessoa reenvie
      a pergunta completa, pois não há memória de conversa.

    Expressões relacionadas ao preço:

    - preço
    - valor
    - quanto custa
    - custo
    - qual o preço

    Todas essas expressões significam consultar a coluna preco.

    Expressões relacionadas ao departamento:

    - departamento
    - categoria
    - setor
    - onde fica
    - pertence a qual departamento

    Todas essas expressões significam consultar a coluna departamento.

    Expressões relacionadas ao vencimento:

    - vencido
    - fora da validade
    - validade acabou
    - já venceu

    Significam data_venci menor que a data atual.

    - vence hoje
    - vencendo hoje

    Significam data_venci igual à data atual.

    - ainda está válido
    - não venceu
    - dentro da validade

    Significam data_venci maior ou igual à data atual.

    REGRAS DE ORDENAÇÃO:

- "mais caro", "maior preço" e "preço mais alto":
  SELECT nome, preco
  FROM produtos
  ORDER BY preco DESC
  LIMIT 1;

- "mais barato", "menor preço" e "preço mais baixo":
  SELECT nome, preco
  FROM produtos
  ORDER BY preco ASC
  LIMIT 1;

Preserve todos os filtros solicitados em WHERE antes de ORDER BY e LIMIT.
Por exemplo, "mais caro de higiene" deve filtrar departamento = 'higiene'.
Não confunda o maior preço de um departamento com o maior preço do estoque.

    REGRAS OBRIGATÓRIAS:

    1. Quando houver informação suficiente, gere exatamente uma consulta SELECT.
    2. Nunca gere INSERT, UPDATE, DELETE, DROP, ALTER, CREATE ou PRAGMA.
    3. Use somente a tabela produtos.
    4. Use somente colunas existentes no schema.
    5. Quando houver um produto específico, filtre pela coluna nome.
    6. Para comparar nomes, utilize LOWER(nome) = LOWER('produto').
    7. Se perguntarem quanto existe de um produto, retorne qntd.
    8. Se perguntarem quantos produtos diferentes existem, use COUNT(*).
    9. Se perguntarem o total de unidades do estoque, use SUM(qntd).
    10. Se perguntarem o valor total do estoque, use SUM(preco * qntd).
    11. Se perguntarem se um produto existe, verifique nome e qntd maior que zero.
    12. Não invente informações que não existem no banco.
    13. Se faltar informação na pergunta, retorne ESCLARECER: e a pergunta
        de esclarecimento. Se faltar um dado no banco, retorne SEM_DADOS:
        e explique a limitação. Nesses casos não gere SQL.
    14. Retorne somente SQL OU uma dessas mensagens, sem Markdown.

    EXEMPLOS DE INTERPRETAÇÃO:

    Pergunta: qual o produto mais caro de higiene?
    SQL: SELECT nome, preco FROM produtos
         WHERE LOWER(departamento) = LOWER('higiene')
         ORDER BY preco DESC LIMIT 1;

    Pergunta: média de preços de higiene fabricados entre 2026-01-01 e 2026-01-31?
    SQL: SELECT AVG(preco) FROM produtos
         WHERE LOWER(departamento) = LOWER('higiene')
         AND data_fabri >= '2026-01-01' AND data_fabri < '2026-02-01';

    Pergunta: média de preços de higiene cadastrados em janeiro?
    Resposta: SEM_DADOS: O banco não possui data de cadastro; só possui
    datas de fabricação e vencimento.

    Pergunta: quais produtos foram fabricados em janeiro?
    Resposta: ESCLARECER: Janeiro de qual ano? Reenvie a pergunta completa
    incluindo o ano.

    Pergunta:
    quanto tem de arroz ainda no estoque?

    SQL:
    SELECT qntd
    FROM produtos
    WHERE LOWER(nome) = LOWER('arroz');

    Pergunta:
    quantas unidades de arroz sobraram?

    SQL:
    SELECT qntd
    FROM produtos
    WHERE LOWER(nome) = LOWER('arroz');

    Pergunta:
    tem arroz disponível?

    SQL:
    SELECT nome, qntd
    FROM produtos
    WHERE LOWER(nome) = LOWER('arroz')
      AND qntd > 0
      AND status = TRUE;

    Pergunta:
    qual o valor do notebook?

    SQL:
    SELECT preco
    FROM produtos
    WHERE LOWER(nome) = LOWER('notebook');

    Pergunta:
    em qual categoria fica o sabonete?

    SQL:
    SELECT departamento
    FROM produtos
    WHERE LOWER(nome) = LOWER('sabonete');

    Pergunta:
    quais produtos estão vencidos?

    SQL:
    SELECT nome, data_venci
    FROM produtos
    WHERE data_venci < DATE('now', 'localtime');

    Pergunta:
    quais produtos vencem hoje?

    SQL:
    SELECT nome, data_venci
    FROM produtos
    WHERE data_venci = DATE('now', 'localtime');

    Pergunta:
    quais produtos ainda estão dentro da validade?

    SQL:
    SELECT nome, data_venci
    FROM produtos
    WHERE data_venci >= DATE('now', 'localtime');

    Pergunta:
    qual é o produto mais caro?

    SQL:
    SELECT nome, preco
    FROM produtos
    ORDER BY preco DESC
    LIMIT 1;

    Pergunta:
    quantos produtos diferentes existem?

    SQL:
    SELECT COUNT(*) AS quantidade_produtos
    FROM produtos;

    Pergunta:
    quantas unidades existem no estoque inteiro?

    SQL:
    SELECT SUM(qntd) AS total_unidades
    FROM produtos;

    Pergunta:
    qual o valor total do estoque?

    SQL:
    SELECT SUM(preco * qntd) AS valor_total
    FROM produtos;

    Pergunta:
    mostre os produtos de higiene que custam menos de 15 reais

    SQL:
    SELECT nome, preco
    FROM produtos
    WHERE LOWER(departamento) = LOWER('higiene')
      AND preco < 15;

    Pergunta:
    qual o preço médio dos produtos?

    SQL:
    SELECT AVG(preco) AS preco_medio
    FROM produtos;

    Pergunta:
    preço médio dos produtos com mais de 100 unidades

    SQL:
    SELECT AVG(preco) AS preco_medio
    FROM produtos
    WHERE qntd > 100;

    Pergunta:
    qual a média de unidades em estoque por produto?

    SQL:
    SELECT AVG(qntd) AS media_unidades
    FROM produtos;

    Pergunta:
    qual produto é o mais barato?

    SQL:
    SELECT nome, preco
    FROM produtos
    ORDER BY preco ASC
    LIMIT 1;

    PESO, TAMANHO E EMBALAGEM:
    Quilos, gramas, litros, ml, peso, tamanho e embalagem estão na descrição
    (coluna produto), nunca em qntd.

    Pergunta:
    quantos quilos tem o pacote de feijão?

    SQL:
    SELECT nome, produto
    FROM produtos
    WHERE LOWER(nome) = LOWER('feijão');

    SINÔNIMOS DE DEPARTAMENTO:
    frutas, legumes e verduras = hortifruti; comida = alimentos;
    eletrônico = eletrônicos; material escolar = papelaria.

    Pergunta:
    qual a média de preço das frutas e legumes?

    SQL:
    SELECT AVG(preco) AS preco_medio
    FROM produtos
    WHERE LOWER(departamento) = LOWER('hortifruti');
    """

    dbschema = dspy.InputField(
        desc="Schema completo da tabela produtos"
    )

    question = dspy.InputField(
        desc=(
            "Pergunta livre em português. Interprete o significado, "
            "mesmo que seja informal ou diferente dos exemplos."
        )
    )

    sql_query = dspy.OutputField(
        desc=(
            "Uma consulta SQLite SELECT ou ESCLARECER: mensagem ou "
            "SEM_DADOS: mensagem, conforme as regras. Sem Markdown."
        )
    )


# ---------------------------------------------------------------------------
# Gerador: chama o LLM, trata ESCLARECER/SEM_DADOS e valida o SQL
# ---------------------------------------------------------------------------
class InterpretationRequired(ValueError):
    """Resposta de interpretação que não deve ser executada como SQL."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


MENSAGEM_INCERTO = (
    "Não tenho certeza da resposta para essa pergunta. "
    "Tente reformular de forma mais direta, ex.: qual o preço médio dos "
    "produtos de limpeza?"
)

# Pergunta -> função SQL obrigatória. Evita, por exemplo, responder
# "preço médio" com o menor preço (erro real visto nos logs).
_EXIGENCIAS_SQL = (
    (re.compile(r"\bm[eé]di[ao]s?\b", re.IGNORECASE), re.compile(r"\bavg\s*\(", re.IGNORECASE)),
    (re.compile(r"\b(soma|somando)\b", re.IGNORECASE), re.compile(r"\bsum\s*\(", re.IGNORECASE)),
)
_AGREGACAO = re.compile(r"\b(avg|sum|count|min|max)\s*\(|\bdistinct\b|\bgroup\s+by\b", re.IGNORECASE)
_LISTA_SELECT = re.compile(r"^\s*select\s+(.*?)\s+from\b", re.IGNORECASE | re.DOTALL)


def sql_combina_com_pergunta(question: str, sql: str) -> bool:
    """
    Checa se o SQL usa a função que a pergunta pede (média -> AVG, soma -> SUM).
    """
    return all(
        sql_exigido.search(sql)
        for pergunta, sql_exigido in _EXIGENCIAS_SQL
        if pergunta.search(question)
    )


def incluir_nome_em_listas(sql: str) -> str:
    """
    Acrescenta a coluna nome em listagens que não a trazem, para a resposta
    não virar uma lista de números soltos ("• 300 un. • 15 un.").
    """
    match = _LISTA_SELECT.search(sql)
    if not match or _AGREGACAO.search(sql) or PADRAO_PRODUTO.search(sql):
        return sql
    colunas = match.group(1)
    if colunas.strip() == "*" or re.search(r"\bnome\b", colunas, re.IGNORECASE):
        return sql
    return sql[:match.start(1)] + "nome, " + sql[match.start(1):]


class ReliableSQLGenerator(dspy.Module):

    def __init__(self):
        super().__init__()
        self.generate_sql = dspy.Predict(TextToSQL)

    def forward(self, schema, question):

        try:
            metrics = request_metrics.get()
            timings = metrics["tempos_segundos"] if metrics is not None else None
            with measure(timings, "geracao_ia"):
                pred = self.generate_sql(dbschema=schema, question=question)

            sql = pred.sql_query.strip()

            sql = sql.replace("```sql", "")
            sql = sql.replace("```", "")
            sql = sql.strip()
            # Remove o marcador final do DSPy antes de validar o SQL.
            sql = sql.removesuffix("[[ ## completed ## ]]").strip()

            for prefix, status in (
                ("ESCLARECER:", "esclarecimento"),
                ("SEM_DADOS:", "informacao_indisponivel"),
            ):
                if sql.startswith(prefix):
                    message = sql[len(prefix):].strip()
                    if not message:
                        raise ValueError("A IA retornou uma mensagem de interpretação vazia.")
                    raise InterpretationRequired(status, message)

            print("SQL gerado:")
            print(sql)

            # Melhor admitir dúvida do que mostrar um número errado com confiança.
            if not sql_combina_com_pergunta(question, sql):
                print("SQL descartado: não combina com a pergunta.")
                raise InterpretationRequired("incerto", MENSAGEM_INCERTO)

            sql = incluir_nome_em_listas(sql)

            if not sql.lower().startswith("select"):
                raise ValueError(
                    "SQL bloqueado: somente consultas SELECT são permitidas."
                )

            if ";" in sql[:-1]:
                raise ValueError(
                    "SQL bloqueado: múltiplas consultas não são permitidas."
                )

            validation_start = perf_counter()
            memory_conn = sqlite3.connect(":memory:")

            try:
                memory_conn.execute(schema)

                memory_conn.execute("""
                    INSERT INTO produtos VALUES
                    (
                        1,
                        'sabonete',
                        'higiene',
                        'Produto de higiene pessoal',
                        12.90,
                        300,
                        '2025-10-13',
                        '2027-09-10',
                        TRUE
                    )
                """)

                memory_conn.execute(sql).fetchall()

                print("SQL validado no SQLite em memória.")

            except sqlite3.Error as e:
                raise ValueError(f"SQL inválido: {e}")

            finally:
                memory_conn.close()
                if timings is not None:
                    timings["validacao_sqlite"] = perf_counter() - validation_start

            return sql

        except InterpretationRequired:
            raise
        except Exception as e:
            print(f"Erro no gerador SQL: {e}")
            raise


generator = ReliableSQLGenerator()


# ---------------------------------------------------------------------------
# Aquecimento: carrega o modelo antes da primeira pergunta
# ---------------------------------------------------------------------------
def warm_up():
    """
    Carrega o modelo no Jan e preenche o cache de prefixo do llama.cpp.
    Ignora o cache em disco do DSPy para que a requisição chegue ao servidor.
    """
    with dspy.context(lm=lm.copy(cache=False)):
        generator.generate_sql(dbschema=SCHEMA, question="quanto custa o arroz?")


# ---------------------------------------------------------------------------
# Ponto de entrada: gera o SQL (com cache), executa e devolve o resultado
# ---------------------------------------------------------------------------
def generate(question):
    """
    Normaliza a pergunta antes de consultar o cache.
    """
    if not question or not question.strip():
        raise ValueError("A pergunta não pode estar vazia.")

    question = " ".join(
        question.lower().strip().split()
    )

    metrics = {
        "cache_sql_hit": True,
        "tempos_segundos": {
            "geracao_ia": 0.0,
            "validacao_sqlite": 0.0,
            "obtencao_sql": 0.0,
            "consulta_banco": 0.0,
        },
    }
    token = request_metrics.set(metrics)
    start = perf_counter()
    rambling = False
    try:
        try:
            # Remove "bom dia", "por favor" etc. e barra o que não é do estoque
            # antes de gastar uma chamada ao LLM.
            with measure(metrics["tempos_segundos"], "filtro"):
                original = question
                status, question = avaliar_pergunta(question, VOCABULARIO_DB)
            if status != "ok":
                print(f"Pergunta barrada pelo filtro ({status}): {question!r}")
                raise InterpretationRequired(status, MENSAGENS[status])
            # Muito texto sem relação: responde a parte útil e o bot dá uma dica.
            rambling = tem_enrolacao(original, question)

            # O modelo responde uma pergunta por vez; o resto volta para o bot.
            question, pending = separar_partes(question)

            with measure(metrics["tempos_segundos"], "obtencao_sql"):
                sql = generate_cached(question, SCHEMA)
            with measure(metrics["tempos_segundos"], "consulta_banco"):
                with closing(sqlite3.connect(db_path)) as conn:
                    conn.execute("PRAGMA query_only = ON")
                    cursor = conn.execute(sql)
                    columns = [col[0] for col in cursor.description]
                    # Uma linha extra indica se o resultado foi cortado.
                    results = cursor.fetchmany(LIMITE_LINHAS + 1)
            truncated = len(results) > LIMITE_LINHAS
            response = {
                "pergunta": question,
                "sql": sql,
                "colunas": columns,
                "resultados": results[:LIMITE_LINHAS],
                "truncado": truncated,
                "pergunta_pendente": pending,
                "enrolacao": rambling,
            }
            # Sem resultado num filtro por nome: sugere nomes parecidos.
            match = PADRAO_PRODUTO.search(sql)
            if match and all(v is None for row in results for v in row):
                response["produto_buscado"] = match.group(1).strip()
                response["sugestoes"] = sugerir_produtos(response["produto_buscado"])
        except InterpretationRequired as clarification:
            response = {
                "pergunta": question,
                "status": clarification.status,
                "mensagem": str(clarification),
                "sql": None,
                "resultados": [],
                "enrolacao": rambling,
            }
        response["metricas"] = metrics
        return response
    finally:
        metrics["tempos_segundos"]["total_servico"] = perf_counter() - start
        request_metrics.reset(token)
        print("METRICAS_SERVICO " + json.dumps(metrics, ensure_ascii=False))


@lru_cache(maxsize=100)
def generate_cached(question, schema=SCHEMA):
    """
    Guarda apenas SQL validado; resultados e métricas nunca entram no cache.
    O schema participa da chave para não reutilizar SQL de outro esquema.
    """
    print("Pergunta enviada para a IA:")
    print(question)

    metrics = request_metrics.get()
    if metrics is not None:
        metrics["cache_sql_hit"] = False
    return generator(schema, question)


# ---------------------------------------------------------------------------
# Execução direta para teste rápido: python fatec.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    create_db()

    question = "quanto custa o arroz?"

    try:
        result = generate(question)

        print("Resultado:")
        print(result)

    except Exception as erro:
        print(f"Erro: {erro}")
