import json
import os
import re
import time

import requests
import telebot
from dotenv import load_dotenv
from timing import measure


load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://127.0.0.1:8000/estoque"

if not API_TOKEN:
    raise RuntimeError(
        "A variável TELEGRAM_BOT_TOKEN não foi encontrada no .env."
    )

bot = telebot.TeleBot(API_TOKEN)


def normalizar_pergunta(texto: str) -> str:
    """
    Converte para minúsculas e remove espaços repetidos.
    """
    return " ".join(texto.lower().strip().split())


def consultar_api(pergunta: str):
    """
    Envia a pergunta para a FastAPI.
    """
    try:
        resposta = requests.get(
            API_URL,
            params={"pergunta": pergunta},
            timeout=(5, 120),
        )

    except requests.Timeout as erro:
        raise RuntimeError(
            "A IA demorou mais de 120 segundos para responder."
        ) from erro

    except requests.ConnectionError as erro:
        raise RuntimeError(
            "Não consegui acessar a API. "
            "Confirme se o Uvicorn está rodando na porta 8000."
        ) from erro

    except requests.RequestException as erro:
        raise RuntimeError(
            f"Erro de comunicação com a API: {erro}"
        ) from erro

    if not resposta.ok:
        try:
            detalhe = resposta.json().get(
                "detail",
                resposta.text,
            )
        except ValueError:
            detalhe = resposta.text

        raise RuntimeError(
            f"A API retornou o erro {resposta.status_code}: {detalhe}"
        )

    return resposta.json()


PADRAO_PRODUTO = re.compile(
    r"nome\)?\s*(?:=|like)\s*(?:lower\()?\s*'%?([^'%]+)%?'",
    re.IGNORECASE,
)


def tipo_coluna(coluna: str) -> str:
    """
    Classifica a coluna pelo nome para escolher o formato do valor.
    """
    coluna = coluna.lower()
    if coluna.startswith("count") or "produtos" in coluna:
        return "contagem"
    if "preco" in coluna or "valor" in coluna:
        return "dinheiro"
    if "qntd" in coluna or "unidades" in coluna:
        return "unidades"
    if "data_venci" in coluna:
        return "vencimento"
    if "data_fabri" in coluna:
        return "fabricacao"
    if "departamento" in coluna:
        return "departamento"
    if "status" in coluna:
        return "status"
    return "texto"


def formatar_numero(valor, casas: int = 0) -> str:
    """
    Formata números no padrão brasileiro (1.234,56).
    """
    texto = f"{float(valor):,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_data(valor) -> str:
    """
    Converte YYYY-MM-DD para DD/MM/YYYY; outros formatos ficam iguais.
    """
    partes = str(valor).split("-")
    if len(partes) == 3:
        return "/".join(reversed(partes))
    return str(valor)


def formatar_valor(coluna: str, valor) -> str:
    """
    Formata um valor isolado para aparecer em uma lista.
    """
    if valor is None:
        return "sem informação"
    tipo = tipo_coluna(coluna)
    if tipo == "dinheiro":
        return f"R$ {formatar_numero(valor, 2)}"
    if tipo == "unidades":
        return f"{formatar_numero(valor)} un."
    if tipo == "contagem":
        return formatar_numero(valor)
    if tipo == "vencimento":
        return f"vence em {formatar_data(valor)}"
    if tipo == "fabricacao":
        return f"fabricado em {formatar_data(valor)}"
    if tipo == "status":
        return "ativo" if valor else "inativo"
    if isinstance(valor, float):
        return formatar_numero(valor, 2)
    return str(valor)


def frase_valor_unico(coluna: str, valor, produto: str | None) -> str:
    """
    Monta uma frase natural para resultados de uma linha e uma coluna.
    """
    tipo = tipo_coluna(coluna)
    agregado = coluna.lower().split("(")[0]
    sujeito = produto.capitalize() if produto else None

    if tipo == "dinheiro":
        preco = f"R$ {formatar_numero(valor, 2)}"
        if agregado == "avg" or "media" in coluna.lower():
            return f"💰 O preço médio é {preco}."
        if agregado == "sum" or "total" in coluna.lower():
            return f"💰 O valor total é {preco}."
        if sujeito:
            return f"💰 {sujeito} custa {preco}."
        return f"💰 O valor é {preco}."

    if tipo == "unidades":
        quantidade = formatar_numero(valor)
        if sujeito:
            return f"📦 Temos {quantidade} unidades de {produto} em estoque."
        return f"📦 São {quantidade} unidades no total."

    if tipo == "contagem":
        return f"🔢 São {formatar_numero(valor)} produtos."

    if tipo == "departamento" and sujeito:
        return f"🏷️ {sujeito} fica no departamento de {valor}."

    if tipo == "vencimento" and sujeito:
        return f"📅 {sujeito} vence em {formatar_data(valor)}."

    if tipo == "fabricacao" and sujeito:
        return f"🏭 {sujeito} foi fabricado em {formatar_data(valor)}."

    return f"✅ {formatar_valor(coluna, valor)}"


def formatar_linha(colunas: list, linha: list) -> str:
    """
    Junta os valores de uma linha, com o nome do produto em destaque.
    """
    return " — ".join(
        formatar_valor(coluna, valor)
        for coluna, valor in zip(colunas, linha)
    )


def formatar_resultado(dados: dict) -> str:
    """
    Transforma o JSON da API em uma resposta em linguagem natural.

    O SQL gerado não é exibido ao usuário; ele continua nos logs da API.
    """
    if dados.get("status") in ("esclarecimento", "informacao_indisponivel"):
        return f"🤔 {dados['mensagem']}"

    colunas = dados.get("colunas") or []
    resultados = dados.get("resultados") or []
    # Agregações sobre zero linhas (ex.: SUM) retornam uma linha com NULL.
    if not resultados or all(
        valor is None for linha in resultados for valor in linha
    ):
        return "🔎 Não encontrei nenhum produto para essa pergunta."

    match = PADRAO_PRODUTO.search(dados.get("sql") or "")
    produto = match.group(1).strip() if match else None

    if len(resultados) == 1 and len(resultados[0]) == 1 and colunas:
        return frase_valor_unico(colunas[0], resultados[0][0], produto)

    if len(resultados) == 1:
        return f"✅ {formatar_linha(colunas, resultados[0])}"

    linhas = "\n".join(
        f"• {formatar_linha(colunas, linha)}" for linha in resultados
    )
    texto = f"Encontrei {len(resultados)} produtos:\n\n{linhas}"
    if dados.get("truncado"):
        texto += "\n\nMostrando só os primeiros resultados. Refine a pergunta para ver menos itens."
    return texto


def dividir_mensagem(texto: str, tamanho: int = 3900):
    """
    Divide respostas maiores que o limite do Telegram.
    """
    return [
        texto[inicio : inicio + tamanho]
        for inicio in range(0, len(texto), tamanho)
    ]


def editar_aviso(aviso, texto: str):
    """
    Edita a mensagem 'Processando...' com o resultado ou erro.
    """
    bot.edit_message_text(
        texto,
        chat_id=aviso.chat.id,
        message_id=aviso.message_id,
    )


@bot.message_handler(commands=["start", "ajuda"])
def ajuda(message):
    bot.reply_to(
        message,
        "Envie uma pergunta sobre o estoque.\n\n"
        "Exemplos:\n"
        "• Quanto tem de arroz no estoque?\n"
        "• Qual item é o mais caro?\n"
        "• Quais produtos estão vencidos?",
    )


@bot.message_handler(content_types=["text"])
def reply_text(message):
    inicio = time.perf_counter()

    pergunta = normalizar_pergunta(message.text)

    print(f"Pergunta recebida: {pergunta}")

    tempos = {}
    aviso = None
    dados = {}
    try:
        with measure(tempos, "telegram_aviso"):
            aviso = bot.reply_to(message, "⏳ Processando sua pergunta...")
        # Inclui rede HTTP, espera e processamento da API; não é só rede.
        with measure(tempos, "api_http"):
            dados = consultar_api(pergunta)

        with measure(tempos, "formatacao"):
            texto = formatar_resultado(dados)
            partes = dividir_mensagem(texto)

        with measure(tempos, "telegram_resposta"):
            # A primeira parte substitui o "Processando..."; o resto segue.
            editar_aviso(aviso, partes[0])
            for parte in partes[1:]:
                bot.send_message(message.chat.id, parte)

    except Exception as erro:
        print(f"Erro ao processar pergunta: {erro}")

        with measure(tempos, "telegram_erro"):
            texto_erro = (
                "😕 Não consegui responder essa pergunta. "
                "Tente reformular de outro jeito.\n\n"
                f"Detalhe: {erro}"
            )
            if aviso is not None:
                editar_aviso(aviso, texto_erro)
            else:
                bot.reply_to(message, texto_erro)
    finally:
        # Medido depois de enviar todas as partes (ou tentar enviar o erro).
        tempos["total_bot"] = time.perf_counter() - inicio
        print("METRICAS_BOT " + json.dumps({
            "chat_id": message.chat.id,
            "message_id": message.message_id,
            "tempos_segundos": tempos,
            "servico": dados.get("metricas"),
        }, ensure_ascii=False))


@bot.message_handler(content_types=["voice"])
def voz_desativada(message):
    bot.reply_to(
        message,
        "A função de voz está temporariamente desativada.",
    )


def start_bot():
    print("Bot iniciado...")

    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30,
    )


if __name__ == "__main__":
    start_bot()
