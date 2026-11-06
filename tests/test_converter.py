"""Verificações de segurança e chamadas do conversor."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

from mindscreen.converter import convert, plan


class ConverterTests(unittest.TestCase):
    def test_protege_raw(self):
        with self.assertRaisesRegex(ValueError, "data/raw"):
            plan(Path("Dados"), Path("data/raw/parquet"))

    def test_nao_permite_saida_na_entrada(self):
        with self.assertRaisesRegex(ValueError, "dentro da pasta"):
            plan(Path("Dados"), Path("Dados/parquet"))

    def test_bloqueia_sobrescrita(self):
        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.is_dir", return_value=True), \
             patch("pathlib.Path.glob", return_value=[Path("origem.csv")]), patch("pathlib.Path.is_file", return_value=True):
            with self.assertRaises(FileExistsError):
                plan(Path("entrada"), Path("saida"))

    def test_converte_como_texto_e_abertura_exclusiva(self):
        tabela = MagicMock()
        pandas = SimpleNamespace(read_csv=MagicMock(return_value=tabela))
        origem, destino = Path("entrada/a.csv"), Path("saida/a.parquet")
        handle = mock_open()
        with patch("mindscreen.converter.plan", return_value=[(origem, destino)]), \
             patch.dict(sys.modules, {"pandas": pandas, "pyarrow": object()}), \
             patch("pathlib.Path.mkdir"), patch("pathlib.Path.open", handle):
            self.assertEqual(convert(Path("entrada"), Path("saida")), [destino])
        pandas.read_csv.assert_called_once_with(origem, dtype=str, keep_default_na=False, skip_blank_lines=False)
        handle.assert_called_once_with("xb")
        tabela.to_parquet.assert_called_once_with(handle(), engine="pyarrow", index=False)


if __name__ == "__main__":
    unittest.main()
