import json
import os

import telebot
import whisper

from fatec import generate

# $env:TELEGRAM_BOT_TOKEN="SEU_TOKEN"
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not API_TOKEN:
    raise RuntimeError("A variável de ambiente TELEGRAM_BOT_TOKEN não foi configurada.")


bot = telebot.TeleBot(API_TOKEN)

WHISPER_MODEL = whisper.load_model("tiny")


def whisper_transcribe(filepath: str) -> str:
    """
    Transcreve um arquivo de áudio usando Whisper.
    """
    result = WHISPER_MODEL.transcribe(filepath)
    return result["text"].strip()


@bot.message_handler(content_types=["text"])
def reply_text(message):
    try:
        result = generate(message.text)

        bot.reply_to(message, json.dumps(result, ensure_ascii=False))

    except Exception as e:
        print(f"Erro ao processar pergunta: {e}")

        bot.reply_to(message, "Ocorreu um erro ao processar sua pergunta.")


@bot.message_handler(content_types=["voice"])
def transcribe_voice_message(message):
    try:
        file_id = message.voice.file_id

        file_path = bot.get_file_url(file_id)

        text = whisper_transcribe(file_path)

        print("Texto transcrito:")
        print(text)

        result = generate(text)

        bot.reply_to(message, json.dumps(result, ensure_ascii=False))

    except Exception as e:
        print(f"Erro ao processar áudio: {e}")

        bot.reply_to(message, "Não consegui processar o áudio.")


def start_bot():
    """
    Inicia o bot do Telegram.
    """
    print("Bot iniciado...")
    bot.infinity_polling()


if __name__ == "__main__":
    start_bot()
