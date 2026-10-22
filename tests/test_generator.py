import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import fatec


class CacheAndTimingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "estoque.db")
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute(fatec.SCHEMA)
            conn.execute("INSERT INTO produtos (id, nome, qntd) VALUES (1, 'arroz', 10)")
        self.db_patch = patch.object(fatec, "db_path", self.path)
        self.db_patch.start()
        fatec.generate_cached.cache_clear()

    def tearDown(self):
        fatec.generate_cached.cache_clear()
        self.db_patch.stop()
        self.directory.cleanup()

    def test_cached_sql_reads_updated_stock_and_has_fresh_metrics(self):
        with patch.object(fatec.generator, "generate_sql", return_value=SimpleNamespace(
            sql_query="SELECT qntd FROM produtos WHERE nome = 'arroz';"
        )) as llm:
            first = fatec.generate(" Quanto tem de ARROZ? ")
            with closing(sqlite3.connect(self.path)) as conn, conn:
                conn.execute("UPDATE produtos SET qntd = 27")
            second = fatec.generate("quanto tem de arroz?")
        self.assertEqual(first["resultados"], [(10,)])
        self.assertEqual(second["resultados"], [(27,)])
        self.assertEqual(llm.call_count, 1)
        self.assertFalse(first["metricas"]["cache_sql_hit"])
        self.assertTrue(second["metricas"]["cache_sql_hit"])
        self.assertGreater(first["metricas"]["tempos_segundos"]["geracao_ia"], 0)
        self.assertEqual(second["metricas"]["tempos_segundos"]["geracao_ia"], 0)
        self.assertEqual(second["metricas"]["tempos_segundos"]["validacao_sqlite"], 0)
        self.assertGreater(second["metricas"]["tempos_segundos"]["consulta_banco"], 0)
        self.assertIsNone(fatec.request_metrics.get())

    def test_clarification_is_not_cached_or_executed(self):
        with patch.object(fatec.generator, "generate_sql", return_value=SimpleNamespace(
            sql_query="SEM_DADOS: Não existe data de cadastro."
        )) as llm, patch.object(fatec.sqlite3, "connect", side_effect=AssertionError):
            for _ in range(2):
                response = fatec.generate("cadastrados em janeiro")
                self.assertEqual(response["status"], "informacao_indisponivel")
                self.assertEqual(response["metricas"]["tempos_segundos"]["consulta_banco"], 0)
            self.assertEqual(llm.call_count, 2)

    def test_failure_does_not_poison_cache_or_context(self):
        with patch.object(fatec.generator, "generate_sql", side_effect=[
            RuntimeError("LLM indisponível"), SimpleNamespace(sql_query="SELECT COUNT(*) FROM produtos;")
        ]):
            with self.assertRaises(RuntimeError):
                fatec.generate("quantos tipos?")
            self.assertIsNone(fatec.request_metrics.get())
            response = fatec.generate("quantos tipos?")
            self.assertFalse(response["metricas"]["cache_sql_hit"])
            self.assertEqual(response["resultados"], [(1,)])


if __name__ == "__main__":
    unittest.main()
