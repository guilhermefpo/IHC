"""Testes do filtro de perguntas (limpeza de "enrolação" e relevância)."""

import unittest

from filtro import avaliar_pergunta, limpar_pergunta, separar_partes, tem_enrolacao

VOCABULARIO = frozenset({"arroz", "feijao", "cafe", "creme dental", "papel-higienico", "higiene"})


class LimparPerguntaTests(unittest.TestCase):
    def test_remove_saudacao_cortesia_e_rodeio(self):
        texto = "Bom dia! Tudo bem? Queria saber, por favor, quanto custa o arroz. Obrigado!"
        self.assertEqual(limpar_pergunta(texto), "quanto custa o arroz")

    def test_remove_rodeio_mas_mantem_a_pergunta(self):
        self.assertEqual(
            limpar_pergunta("tem como saber o preço do café?"), "o preço do café"
        )
        self.assertEqual(
            limpar_pergunta("você poderia me dizer quais produtos estão vencidos?"),
            "quais produtos estão vencidos",
        )

    def test_nao_corta_palavras_soltas(self):
        self.assertEqual(limpar_pergunta("tem arroz?"), "tem arroz")
        self.assertEqual(limpar_pergunta("quanto tem de feijão"), "quanto tem de feijão")

    def test_mantem_acentos(self):
        self.assertIn("feijão", limpar_pergunta("oi, quanto custa o feijão?"))


class AvaliarPerguntaTests(unittest.TestCase):
    def avaliar(self, texto):
        return avaliar_pergunta(texto, VOCABULARIO)[0]

    def test_saudacao_pura(self):
        for texto in ("bom dia", "Oi, tudo bem?", "olá!", "e aí, beleza?"):
            with self.subTest(texto=texto):
                self.assertEqual(self.avaliar(texto), "saudacao")

    def test_agradecimento(self):
        for texto in ("obrigado!", "valeu", "muito obrigada, boa noite"):
            with self.subTest(texto=texto):
                self.assertEqual(self.avaliar(texto), "agradecimento")

    def test_fora_do_escopo(self):
        for texto in (
            "qual a capital da França?",
            "me conta uma piada",
            "quem ganhou o jogo ontem?",
            "bom dia, como está o clima hoje?",
        ):
            with self.subTest(texto=texto):
                self.assertEqual(self.avaliar(texto), "fora_do_escopo")

    def test_perguntas_do_estoque_passam(self):
        for texto in (
            "quanto custa o arroz?",
            "tem arroz?",
            "bom dia! quanto tem de feijão por favor",
            "qual o mais caro?",
            "quais produtos estão vencidos?",
            "qual o valor total do estoque?",
            "em que setor fica o café?",
            "quanto custa o creme dental?",
            "tem papel-higiênico?",
            "quantos tipos de produto existem?",
        ):
            with self.subTest(texto=texto):
                self.assertEqual(self.avaliar(texto), "ok")

    def test_confirmacao(self):
        self.assertEqual(self.avaliar("ok"), "confirmacao")
        self.assertEqual(self.avaliar("ok obrigado"), "agradecimento")

    def test_pedido_de_alteracao(self):
        for texto in ("altere todos os status para inativo", "apague o arroz", "mude o preço do café"):
            with self.subTest(texto=texto):
                self.assertEqual(self.avaliar(texto), "alteracao")

    def test_pedido_nao_suportado(self):
        texto = "com base nos 50 produtos, gostaria de um mapa mental dos preços"
        self.assertEqual(self.avaliar(texto), "nao_suportado")

    def test_ofensa_so_fora_do_estoque(self):
        self.assertEqual(self.avaliar("vai tomar no olho do seu cu"), "ofensa")
        self.assertEqual(self.avaliar("porra, quanto custa o arroz?"), "ok")

    def test_descarta_frases_sem_relacao(self):
        status, limpo = avaliar_pergunta(
            "Bom dia, Enermich. Quanto custa o arroz?", VOCABULARIO
        )
        self.assertEqual((status, limpo), ("ok", "quanto custa o arroz"))

    def test_saude(self):
        for texto in (
            "estou passando muito mal, preciso de um remédio. quais produtos você indica?",
            "estou muito doente",
        ):
            with self.subTest(texto=texto):
                self.assertEqual(self.avaliar(texto), "saude")

    def test_palavras_comuns_nao_casam_por_aproximacao(self):
        # "estou" ~ "estoque", "preso" ~ "peso" e "preciso" ~ "preço" (logs reais).
        for texto in (
            "eu estou jogando um jogo e estou preso em um chefe",
            "eu preciso da sua ajuda",
        ):
            with self.subTest(texto=texto):
                self.assertEqual(self.avaliar(texto), "fora_do_escopo")

    def test_troca_sinonimos_de_departamento(self):
        status, limpo = avaliar_pergunta(
            "qual a média do valor dos produtos de legumes e frutas?", VOCABULARIO
        )
        self.assertEqual((status, limpo), ("ok", "qual a média do valor dos produtos de hortifruti"))

    def test_tolera_erro_de_digitacao(self):
        self.assertEqual(self.avaliar("tem arros?"), "ok")
        self.assertEqual(self.avaliar("qto ta o feijao"), "ok")
        self.assertEqual(self.avaliar("produtos vencios"), "ok")


class TemEnrolacaoTests(unittest.TestCase):
    def enrolacao(self, texto):
        _, pergunta = avaliar_pergunta(texto, VOCABULARIO)
        return tem_enrolacao(texto, pergunta)

    def test_historia_com_pergunta_no_final(self):
        self.assertTrue(self.enrolacao(
            "eu estou jogando um jogo e estou preso em um chefe muito difícil. "
            "para derrotar ele preciso resolver um enigma. "
            "qual o preço do arroz?"
        ))

    def test_cortesia_nao_conta_como_enrolacao(self):
        self.assertFalse(self.enrolacao(
            "Bom dia! Tudo bem? Será que você consegue me dizer, por favor, quanto custa o arroz?"
        ))

    def test_pergunta_direta(self):
        self.assertFalse(self.enrolacao("quanto custa o arroz?"))


class SepararPartesTests(unittest.TestCase):
    def test_separa_segunda_pergunta(self):
        primeira, resto = separar_partes(
            "a média do valor dos produtos de limpeza. aí depois você faça o de legumes"
        )
        self.assertEqual(primeira, "a média do valor dos produtos de limpeza")
        self.assertEqual(resto, "o de legumes")

    def test_pergunta_unica_fica_igual(self):
        self.assertEqual(separar_partes("quanto custa o arroz"), ("quanto custa o arroz", ""))


if __name__ == "__main__":
    unittest.main()
