"""Testes das barreiras para análise e treinamento."""

import hashlib
import io
import json
import unittest
from unittest.mock import patch

from mindscreen.dados_validados import check_predictors, load_manifest, safe_output


class ValidatedDataTests(unittest.TestCase):
    def test_requires_screen_time_and_unique_columns(self):
        with self.assertRaises(ValueError):
            check_predictors([], ["SC_SEX"])
        with self.assertRaises(ValueError):
            check_predictors(["SCREENTIME"], ["screentime"])
        check_predictors([], ["SCREENTIME", "SC_SEX"])

    def test_prohibits_both_target_families_and_survey_identifiers(self):
        for feature in ["K2Q32A", "k2q32c", "K2Q33B", "K2Q33C", "depressao_atual", "ansiedade_atual", "FWC", "ano", "HHID"]:
            with self.subTest(feature=feature), self.assertRaises(ValueError):
                check_predictors([], ["SCREENTIME", feature])

    def test_refuses_output_in_raw(self):
        with self.assertRaises(ValueError):
            safe_output("data/raw/resultado")

    def test_manifest_requires_validation_and_matching_hash(self):
        data = b"bytes teste"
        manifest = {"validado": True, "aprovado_por": "revisor", "documentacao_validacao": "doc",
                    "classe_positiva": 1, "dataset": "dataset.parquet", "sha256": hashlib.sha256(data).hexdigest(),
                    "preditores_numericos": [], "preditores_categoricos": ["SCREENTIME"]}
        with patch("pathlib.Path.read_text", return_value=json.dumps(manifest)), patch("pathlib.Path.open", return_value=io.BytesIO(data)):
            loaded, _ = load_manifest("manifesto.json")
        self.assertEqual(loaded["sha256"], manifest["sha256"])
        manifest["sha256"] = "0" * 64
        with patch("pathlib.Path.read_text", return_value=json.dumps(manifest)), patch("pathlib.Path.open", return_value=io.BytesIO(data)):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_manifest("manifesto.json")
        manifest["validado"] = False
        with patch("pathlib.Path.read_text", return_value=json.dumps(manifest)):
            with self.assertRaisesRegex(ValueError, "não validado"):
                load_manifest("manifesto.json")


if __name__ == "__main__":
    unittest.main()
