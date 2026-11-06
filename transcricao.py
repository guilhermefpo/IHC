"""Transcreve mensagens de voz do Telegram para texto com faster-whisper (local).

O modelo roda na CPU, sem internet depois do primeiro download (~460 MB no
caso do "small"), e lê o OGG/Opus do Telegram direto, sem precisar de ffmpeg.
"""

import io
import os
import threading

from faster_whisper import WhisperModel

# ---------------------------------------------------------------------------
# Modelo: carregado uma vez; int8 em CPU equilibra velocidade e memória
# ---------------------------------------------------------------------------
_modelo = WhisperModel(
    os.getenv("WHISPER_MODEL", "small"),
    device="cpu",
    compute_type="int8",
    cpu_threads=4,
)
# O bot atende em 2 threads; o lock evita duas transcrições disputando a CPU.
_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Ajustes de qualidade para o domínio do estoque
# ---------------------------------------------------------------------------
# Vocabulário do domínio melhora o reconhecimento dos nomes de produtos.
VOCABULARIO = (
    "Perguntas sobre estoque: preço, quantidade, validade, departamento. "
    "Produtos: arroz, feijão, café, notebook, sabonete, detergente, shampoo."
)

# Frases que o Whisper costuma "inventar" em áudios mudos ou com ruído.
ALUCINACOES = (
    "amara.org",
    "legendas pela comunidade",
    "obrigado por assistir",
    "inscreva-se",
)


# ---------------------------------------------------------------------------
# Transcrição
# ---------------------------------------------------------------------------
def transcrever(audio: bytes) -> str:
    """
    Converte o áudio (OGG/Opus do Telegram) em texto em português.
    Retorna string vazia quando não há fala reconhecível.
    """
    with _lock:
        segmentos, _ = _modelo.transcribe(
            io.BytesIO(audio),
            language="pt",
            beam_size=1,  # Mais rápido; frases curtas não ganham com beam maior.
            vad_filter=True,  # Corta silêncio e reduz alucinações.
            initial_prompt=VOCABULARIO,
        )
        # Descarta trechos que o modelo marcou como provável silêncio/ruído.
        texto = " ".join(
            s.text.strip() for s in segmentos if s.no_speech_prob < 0.6
        ).strip()

    if any(frase in texto.lower() for frase in ALUCINACOES):
        return ""
    return texto


if __name__ == "__main__":
    # Teste rápido: python transcricao.py caminho/do/audio.ogg
    import sys

    with open(sys.argv[1], "rb") as arquivo:
        print(transcrever(arquivo.read()))
