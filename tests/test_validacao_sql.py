"""Testes das checagens do SQL gerado e das sugestões de nomes (fatec.py)."""

import unittest
from unittest.mock import patch

import fatec


class SqlCombinaComPerguntaTests(unittest.TestCase):
    def test_media_exige_avg(self):
        self.assertFalse(fatec.sql_combina_com_pergunta(
            "preço médio dos produtos",
            "SELECT preco AS preco_medio FROM produtos ORDER BY preco ASC LIMIT 1;",
        ))
        self.assertTrue(fatec.sql_combina_com_pergunta(
            "preço médio dos produtos", "SELECT AVG(preco) FROM produtos;"
        ))

    def test_soma_exige_sum(self):
        self.assertFalse(fatec.sql_combina_com_pergunta(
            "soma das unidades", "SELECT qntd FROM produtos;"
        ))

    def test_pergunta_sem_exigencia_passa(self):
        self.assertTrue(fatec.sql_combina_com_pergunta(
            "quanto custa o arroz", "SELECT preco FROM produtos WHERE nome = 'arroz';"
        ))


class IncluirNomeEmListasTests(unittest.TestCase):
    def test_lista_sem_nome_ganha_nome(self):
        self.assertEqual(
            fatec.incluir_nome_em_listas("SELECT qntd FROM produtos WHERE status = TRUE;"),
            "SELECT nome, qntd FROM produtos WHERE status = TRUE;",
        )

    def test_nao_mexe_quando_nao_precisa(self):
        for sql in (
            "SELECT nome, preco FROM produtos;",
            "SELECT AVG(preco) FROM produtos;",
            "SELECT DISTINCT departamento FROM produtos;",
            "SELECT * FROM produtos;",
            "SELECT qntd FROM produtos WHERE LOWER(nome) = LOWER('arroz');",
        ):
            with self.subTest(sql=sql):
                self.assertEqual(fatec.incluir_nome_em_listas(sql), sql)


class SugerirProdutosTests(unittest.TestCase):
    def test_sugere_nome_contido_e_parecido(self):
        with patch.object(fatec, "PRODUTOS_DB", ("arroz", "feijão", "queijo", "café")):
            self.assertEqual(fatec.sugerir_produtos("feijão carioca"), ["feijão"])
            self.assertIn("arroz", fatec.sugerir_produtos("arros"))
            self.assertEqual(fatec.sugerir_produtos("notebook"), [])


if __name__ == "__main__":
    unittest.main()
