"""Testes de descoberta e auditoria sem depender de microdados reais."""

import json
from contextlib import contextmanager
import shutil
from uuid import uuid4
import unittest
from pathlib import Path
from unittest.mock import patch

from mindscreen.auditoria import audit, audit_csv, write_reports
from mindscreen.importacao import discover, read_file


@contextmanager
def workspace_directory():
    """Diretório isolado com permissões herdadas, compatível com Windows restrito."""
    root = (Path(__file__).resolve().parents[1] / ".tmp").resolve()
    folder = root / ("test-auditoria-" + uuid4().hex)
    folder.mkdir(parents=True)
    try:
        yield folder
    finally:
        resolved = folder.resolve()
        if root not in resolved.parents:
            raise ValueError("Diretório de teste fora da pasta temporária do projeto")
        shutil.rmtree(resolved)


class AuditTests(unittest.TestCase):
    def test_discovers_nested_and_does_not_change_raw(self):
        with workspace_directory() as temp:
            raw = Path(temp)
            (raw / "2021").mkdir()
            original = raw / "2021" / "nsch_2021e_topical.dta"
            original.write_bytes(b"original")
            (raw / "2024_screener.sas7bdat").write_bytes(b"data")
            (raw / "ignored.txt").write_text("ignored")
            found = discover(raw)
            self.assertEqual(len(found), 2)
            item = next(x for x in found if x.path == original)
            self.assertEqual(item.year, 2021)
            self.assertTrue(item.topical_hint)
            self.assertTrue(item.enhanced_hint)
            self.assertEqual(original.read_bytes(), b"original")
            self.assertFalse(next(x for x in found if x.year == 2024).topical_hint)

    def test_conflicting_years_are_not_inferred(self):
        with workspace_directory() as temp:
            folder = Path(temp) / "2020"
            folder.mkdir()
            (folder / "nsch_2021_topical.dta").touch()
            self.assertIsNone(discover(Path(temp))[0].year)

    def test_unsupported_format(self):
        with self.assertRaises(ValueError):
            read_file(Path("x.txt"))

    def test_csv_counts_empty_and_preserves_codes(self):
        from io import StringIO
        with patch("pathlib.Path.open", return_value=StringIO("SCREENTIME,K2Q32A\n1,2\n,\n3,9\n")):
            rows, columns, missing, values = audit_csv(Path("test.csv"), 2020)
        self.assertEqual(rows, 3)
        self.assertEqual(len(columns), 2)
        self.assertEqual(missing[0]["ausentes_sistema"], 1)
        self.assertIn({"arquivo": "test.csv", "ano": 2020, "variavel": "K2Q32A", "valor": "9", "contagem": 1}, values)

    def test_read_dispatches_without_value_recode(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import Mock
        read_dta, read_sas = Mock(return_value=("data", "metadata")), Mock(return_value=("data", "metadata"))
        with patch.dict(sys.modules, {"pyreadstat": SimpleNamespace(read_dta=read_dta, read_sas7bdat=read_sas)}):
            self.assertEqual(read_file(Path("x.dta")), ("data", "metadata"))
            read_file(Path("x.sas7bdat"))
        read_dta.assert_called_once_with("x.dta", user_missing=True, apply_value_formats=False)
        read_sas.assert_called_once_with("x.sas7bdat", user_missing=True)

    def test_importacao_dta_real_preserva_codigos_sem_aplicar_rotulos(self):
        import pandas as pd
        import pyreadstat
        with workspace_directory() as temp:
            path = temp / "fixture_sintetica.dta"
            pyreadstat.write_dta(pd.DataFrame({"resposta": [1.0, 2.0]}), str(path), variable_value_labels={"resposta": {1: "Sim", 2: "Não"}})
            frame, _ = read_file(path)
            self.assertEqual(frame.resposta.tolist(), [1.0, 2.0])

    def test_missing_years_and_errors_do_not_abort(self):
        with workspace_directory() as temp:
            raw = Path(temp) / "raw"
            raw.mkdir()
            (raw / "nsch_2020_topical.dta").touch()
            with patch("mindscreen.auditoria.read_file", side_effect=ValueError("inválido")):
                report = audit(raw)
            self.assertEqual(len(report["erros"]), 1)
            self.assertEqual(report["anos_sem_arquivo"], [2021, 2022, 2023, 2024])
            self.assertEqual(report["disponibilidade"][0]["classificacao"], "Ano não auditado")
            self.assertFalse(report["arquivos"][0]["validado"])
            out = Path(temp) / "reports"
            write_reports(report, out)
            self.assertEqual(len(json.loads((out / "auditoria.json").read_text(encoding="utf-8"))["erros"]), 1)
            self.assertTrue((out / "matriz.csv").exists())


if __name__ == "__main__":
    unittest.main()
