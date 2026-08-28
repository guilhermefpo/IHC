import json
import os

import telebot
import whisper

from IHC.server import generate

API_TOKEN = os.getenv("T8769535499:AAH4aKI1oeCsL61jeIWU9b_pRCsuBtDvFyo")

bot = telebot.TeleBot(API_TOKEN)


@bot.message_handler(content_types=["text"])
def reply_text(message):

    try:
        result = generate(message.text)

        bot.reply_to(message, json.dumps(result, ensure_ascii=False))

    except Exception as e:

        print(f"Erro: {e}")

        bot.reply_to(message, "Ocorreu um erro ao processar sua pergunta.")


@bot.message_handler(content_types=["voice"])
def transcribe_voice_message(message):

    try:

        file_id = message.voice.file_id

        file_path = bot.get_file_url(file_id)

        # Transcrição
        text = whisper_transcribe(file_path)

        print("Texto transcrito:")
        print(text)

        result = generate(text)

        bot.reply_to(message, json.dumps(result, ensure_ascii=False))

    except Exception as e:

        print(f"Erro: {e}")

        bot.reply_to(message, "Não consegui processar o áudio.")


def whisper_transcribe(filepath: str, model="tiny") -> str:
    """
    Transcreve um arquivo de áudio usando Whisper.

    Modelos disponíveis:
    tiny
    base
    small
    medium
    large
    """

    model = whisper.load_model(model)

    result = model.transcribe(filepath)

    return result["text"]


if __name__ == "__main__":

    print("Bot iniciado...")

    bot.polling()
