"""Teste em memória com dados sintéticos, sem uso de microdados ou artefatos reais."""

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

pd = pytest.importorskip("pandas")
joblib = pytest.importorskip("joblib")
pytest.importorskip("sklearn")
pytest.importorskip("xgboost")

from mindscreen.treinamento import train
from mindscreen.dados_validados import load_dataset


def test_exige_pesos_e_estrato_no_dataset_validado():
    manifest = {"preditores_numericos": [], "preditores_categoricos": ["SCREENTIME"]}
    frame = pd.DataFrame({"ano": [2020], "SCREENTIME": ["1"], "depressao_atual": [0], "ansiedade_atual": [0]})
    with patch("mindscreen.dados_validados.load_manifest", return_value=(manifest, Path("dados.parquet"))), \
         patch.object(pd, "read_parquet", return_value=frame):
        with pytest.raises(ValueError, match="FWC.*STRATUM"):
            load_dataset(Path("manifesto"))


def test_treinamento_isola_2024_e_persiste_pipeline_completo():
    rows = [{"ano": year, "SCREENTIME": "SO_2024" if year == 2024 else str(i % 3),
             "idade": float(i) if i != 0 else None,
             "depressao_atual": 99 if year == 2024 else i % 2,
             "ansiedade_atual": 99 if year == 2024 else (i // 2) % 2}
            for year in range(2020, 2025) for i in range(8)]
    frame = pd.DataFrame(rows)
    manifest = {"preditores_numericos": ["idade"], "preditores_categoricos": ["SCREENTIME"], "sha256": "teste"}
    config = {"ano_teste": 2024, "anos_desenvolvimento": [2020, 2021, 2022, 2023], "folds": 5,
              "semente": 42, "n_jobs": 1, "n_estimators": 2,
              "busca": {"logistic": {"model__C": [1.0]}, "random_forest": {"model__max_depth": [2]},
                        "xgboost": {"model__max_depth": [2]}}}
    saved = {}
    log = {}
    dump_original = joblib.dump

    def capture(model, path):
        buffer = BytesIO()
        dump_original(model, buffer)
        buffer.seek(0)
        saved[path.name] = joblib.load(buffer)

    def capture_log(path, content, **kwargs):
        log.update(json.loads(content))

    with patch("mindscreen.treinamento.load_dataset", return_value=(manifest, frame)), \
         patch("mindscreen.treinamento.version", return_value="fixture"), \
         patch("pathlib.Path.read_text", return_value=json.dumps(config)), \
         patch("pathlib.Path.mkdir"), patch("pathlib.Path.write_text", new=capture_log), \
         patch.object(joblib, "dump", side_effect=capture):
        train(Path("manifesto-teste"), Path("config-teste"), Path("models/fixture-nao-gravada"))

    assert len(saved) == 8
    for model in saved.values():
        encoder = model.named_steps["preprocess"].named_transformers_["categoricas"].named_steps["encode"]
        assert "SO_2024" not in encoder.categories_[0]
        probabilities = model.predict_proba(pd.DataFrame({"idade": [None], "SCREENTIME": ["SO_2024"]}))
        assert probabilities.shape == (1, 2)
    for result in log["resultados"].values():
        assert result["registros"] == 32
        assert result["classes"] == {"0": 16, "1": 16}
        assert all(not m["sample_weight_utilizado"] for m in result["modelos"].values())
