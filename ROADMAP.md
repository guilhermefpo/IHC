# Roadmap — Bot de Estoque (Text-to-SQL)

> Este roadmap foi montado a partir da estrutura do projeto, não do enunciado
> da disciplina. Ajuste as prioridades conforme os critérios de avaliação.

## Fase 1 — Corrigir o que está quebrado ou arriscado (1–2 dias)

- [ ] **Tirar o `.env` do git.** Rodar `git rm --cached .env` e criar um
  `.env.example` só com os nomes das variáveis. Se algum token já subiu para
  o GitHub, gerar outro no BotFather.
- [ ] **Tirar `__pycache__/*.pyc` do repositório.** Esses arquivos são gerados
  automaticamente e não devem ser commitados.
- [ ] **Ter um único banco e um único schema.** Hoje existem dois bancos
  diferentes:
  - `fatec.py` usa `lojas.db` com uma tabela só, `produtos`, e colunas como
    `qntd` e `data_venci`;
  - `app/database/schema.sql` define as tabelas `departamentos` e `produtos`
    com chave estrangeira.

  Escolher um dos dois. Se o requisito pedir modelagem com relacionamento,
  usar o de `app/`.
- [ ] **Adicionar um `requirements.txt` com versões fixas.** Sem ele, o
  projeto depende do Python instalado na máquina.
- [ ] **Corrigir `app/integrations/whisper_service.py`.** O arquivo tem só o
  texto `py list`, digitado por engano.

## Fase 2 — Organizar a arquitetura (2–3 dias)

Hoje tudo fica em `fatec.py`. A ideia é dividir o código nos arquivos vazios
que já existem em `app/`:

| Arquivo | O que vai nele |
|---|---|
| `app/text_to_sql/signature.py` | Assinatura `TextToSQL` (o prompt) |
| `app/text_to_sql/generator.py` | `ReliableSQLGenerator` e o cache |
| `app/text_to_sql/validator.py` | Validação: só `SELECT`, uma consulta por vez, tabelas permitidas |
| `app/text_to_sql/schema.py` | Schema lido direto do banco, em vez de texto fixo no código |
| `app/database/repository.py` | Execução das consultas em modo somente leitura |
| `app/services/estoque_service.py` | Orquestra o fluxo: pergunta → SQL → consulta → resposta |
| `app/api/consulta_routes.py` | Rota de consulta em linguagem natural |
| `app/api/produtos_routes.py` | Rotas de produtos |
| `app/integrations/telegram_bot.py` | Código atual do `bot.py` |

- [ ] No fim, `server.py`, `bot.py` e `fatec.py` viram só pontos de entrada
  finos ou são removidos.

## Fase 3 — Funcionalidades que faltam (3–5 dias)

- [ ] **Voz.** Implementar `whisper_service.py` (transcrição local com
  faster-whisper ou o Whisper do Jan) e reativar o handler de voz do bot. É um
  diferencial forte para uma disciplina de IHC.
- [ ] **Rotas de produtos (CRUD)** em `produtos_routes.py`, se o requisito
  pedir gestão de estoque. O bot continua apenas consultando.
- [ ] **Memória curta de conversa**, por exemplo "e o feijão?" depois de
  "quanto custa o arroz?". Hoje cada mensagem é tratada de forma independente.
- [ ] **Comandos de atalho no Telegram** (`/vencidos`, `/estoque_baixo`,
  `/departamentos`) com SQL fixo. São respostas instantâneas e sem risco de o
  modelo gerar SQL errado.

## Fase 4 — Medir a qualidade (2–3 dias)

- [ ] **Montar o conjunto de avaliação** em `app/evaluation/questions.json`,
  com 50 ou mais perguntas e o SQL ou resultado esperado de cada uma.
- [ ] **Escrever o avaliador.** `metrics.py` e `evaluator.py` comparam o
  resultado da consulta gerada com o esperado (mais robusto que comparar o
  texto do SQL) e medem a latência. O script `scripts/evaluate.py` gera um
  relatório.
- [ ] **Otimizar o prompt com GEPA/DSPy** (`gepa_optimizer.py` e
  `scripts/optimize.py`), usando esse conjunto, e mostrar a acurácia antes e
  depois. É isso que transforma o projeto de "funciona" em "funciona e prova
  que funciona".
- [ ] **Testar o modelo no Jan:**
  - trocar para o Qwen3-0.6B **Q8_0** e definir `JAN_MODEL` no `.env`;
  - medir com GPU Layers 0 e com 99;
  - comparar acurácia e latência entre as configurações.

## Fase 5 — Testes e entrega (1–2 dias)

- [ ] **Preencher os arquivos de teste vazios:**
  - `tests/test_validator.py`: SQL malicioso bloqueado, como `DROP` e
    múltiplas consultas;
  - `tests/test_database.py`;
  - `tests/test_api.py`, usando o `TestClient` do FastAPI;
  - testes do `formatar_resultado`.
- [ ] **Reescrever o README** com:
  - arquitetura em diagrama;
  - como instalar e configurar o Jan;
  - como rodar o projeto;
  - exemplos de perguntas;
  - métricas de acurácia e latência;
  - limitações conhecidas.
- [ ] **Preparar a demonstração:** um vídeo curto do bot respondendo por texto
  e por voz.

## Prioridade se o tempo for curto

1. Fase 1
2. Avaliação com métricas (Fase 4, itens 1 e 2)
3. Testes do validador
4. README
5. Voz
6. Reorganização da arquitetura

A reorganização vale menos nota que provar com números que o bot acerta e é
seguro.
