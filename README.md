# Bot de Estoque — Text-to-SQL com LLM local

Bot do Telegram que responde perguntas sobre o estoque em português. Um modelo
de linguagem local (Qwen3-0.6B rodando no Jan) transforma a pergunta em uma
consulta SQL. O resultado da consulta volta ao usuário como uma frase natural.

## Como funciona

```
Usuário (Telegram)
   │  "quanto custa o feijão?"
   ▼
bot.py ──HTTP──▶ server.py ──▶ fatec.py ──▶ Jan (Qwen3) ──▶ SQL
   ▲                              │
   │                              ▼
   │                         lojas.db (SQLite)
   │                              │
   └──── "💰 Feijão custa R$ 8,99." ◀── colunas + linhas
```

1. **`bot.py`** recebe a mensagem e envia a pergunta para a API. Se for um
   áudio, `transcricao.py` primeiro converte a fala em texto e o bot mostra
   o que entendeu.
2. **`server.py`** repassa a pergunta para `generate()`.
3. **`fatec.py`**:
   - normaliza a pergunta e procura o SQL no cache;
   - se não houver, pede o SQL ao LLM;
   - valida o SQL (só `SELECT`, testado antes num banco em memória);
   - executa no `lojas.db` em modo somente leitura.
4. **`bot.py`** transforma as colunas e linhas em frases, sem chamar o LLM de
   novo, e responde no chat.

Se a pergunta for ambígua ou pedir um dado que não existe no banco, o modelo
responde `ESCLARECER:` ou `SEM_DADOS:`. Nesses casos o bot repassa a mensagem
ao usuário e nenhum SQL é executado.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `bot.py` | Bot do Telegram: recebe perguntas, chama a API, formata a resposta (preços em R$, datas DD/MM/AAAA, listas) e divide mensagens longas. |
| `server.py` | API FastAPI. Na inicialização cria o banco e aquece o modelo. Rota `GET /estoque?pergunta=...`. |
| `fatec.py` | Núcleo Text-to-SQL. Contém:<br>• criação e carga do banco;<br>• configuração do LLM;<br>• prompt com regras e exemplos (`TextToSQL`);<br>• gerador com validação (`ReliableSQLGenerator`);<br>• cache e execução da consulta (`generate`). |
| `transcricao.py` | Transcreve mensagens de voz em português com faster-whisper (local, CPU). Filtra silêncio e frases inventadas pelo modelo. |
| `timing.py` | Mede o tempo de cada etapa. Os tempos aparecem nos logs `METRICAS_BOT` e `METRICAS_SERVICO`. |
| `lojas.db` | Banco SQLite com a tabela `produtos` (50 itens de exemplo). |
| `tests/test_generator.py` | Testes do cache, das métricas e das respostas de esclarecimento (o LLM é simulado). |
| `.env` | Configuração local; não deve ir para o git. |
| `ROADMAP.md` | Próximas etapas do projeto. |

## Configuração

Crie um `.env` na raiz do projeto:

```
TELEGRAM_BOT_TOKEN=seu_token_do_botfather
JAN_MODEL=Qwen3-0_6B-BF16              # opcional
JAN_API_BASE=http://127.0.0.1:1337/v1  # opcional
WHISPER_MODEL=small                    # opcional: tiny, base, small
```

No Jan:

1. Baixe o modelo Qwen3-0.6B.
2. Ligue o **Local API Server** na porta 1337.
3. Recomendado: mude **Parallel** para 1 em *Model Providers → llama.cpp*.

## Como rodar

Instale as dependências:

```
pip install -r requirements.txt
```

Em um terminal, suba a API:

```
python -m uvicorn server:app --port 8000
```

Em outro terminal, suba o bot:

```
python bot.py
```

Para rodar os testes:

```
python -m unittest tests.test_generator
```

## Desempenho

O modo "thinking" do Qwen3 fica desligado e a resposta é limitada a 200
tokens. A primeira consulta é aquecida na inicialização da API. Com isso, cada
pergunta nova leva cerca de 2,5–4,5 s neste notebook, contra 25–33 s antes.
Perguntas repetidas são respondidas pelo cache, sem chamar o LLM.

## Exemplos de perguntas

- Quanto custa o arroz?
- Quanto tem de café no estoque?
- Qual o produto mais caro de higiene?
- Quais produtos estão vencidos?
- Qual o valor total do estoque?
