"""Integração com artefatos reais, quando disponíveis, sem treinar na interface."""

import json
from pathlib import Path

import pytest

from mindscreen.artefatos import load_model, read_registry
from mindscreen.avaliacao import positive_probability
from mindscreen.dados_validados import load_dataset
from mindscreen.inferencia import predict_profile, profile_frame
from mindscreen.painel import json_result

REGISTRY = Path("models/experimentos/registro.json")


def require_results():
    if not REGISTRY.exists() or not Path("reports/avaliacao/avaliacao.json").exists():
        pytest.skip("Experimentos reais ainda não concluídos")


def test_metricas_modelos_e_interface_usam_mesmo_dataset():
    require_results()
    manifest, frame = load_dataset("data/processed/manifesto.json")
    registry = read_registry(REGISTRY)
    evaluation = json_result("reports/avaliacao/avaliacao.json", manifest["sha256"])
    assert len(evaluation["metricas"]) == 16
    rules = json.loads(Path("configs/harmonizacao.json").read_text(encoding="utf-8"))
    profile = {"SC_AGE_YEARS": 12, "SCREENTIME": 3, "SC_SEX": 1, "HOURSLEEP": 4, "PHYSACTIV": 2, "MAKEFRIEND": 1}
    X = profile_frame(profile, manifest, rules)
    predictions = predict_profile(profile, manifest, rules, REGISTRY)
    for target, value in predictions.items():
        model = load_model(REGISTRY, registry["selecionados"]["A/" + target], manifest["sha256"])
        assert positive_probability(model, X)[0] == value["score"]
        assert value["calibrado"] is False
    for metric in evaluation["metricas"]:
        expected = int((frame.ano.eq(2024) & frame[metric["target"]].notna()).sum())
        assert metric["n"] == expected
        assert metric["tn"] + metric["fp"] + metric["fn"] + metric["tp"] == expected
        assert metric["positivos"] == metric["fn"] + metric["tp"]


def test_streamlit_paginas_e_formulario_reais(monkeypatch):
    require_results()
    if not Path("reports/figures/explicabilidade.json").exists():
        pytest.skip("Explicabilidade ainda não concluída")
    import tempfile
    from uuid import uuid4
    def inherited_temp(*args, **kwargs):
        root = Path(".tmp").resolve()
        folder = root / ("streamlit-test-" + uuid4().hex)
        if root not in folder.resolve().parents:
            raise ValueError("Diretório de teste fora da pasta autorizada")
        folder.mkdir(parents=True)
        return str(folder)
    # Evita a ACL privada 0700 do tempfile de Python 3.14 no Windows restrito.
    with monkeypatch.context() as scope:
        scope.setattr(tempfile, "mkdtemp", inherited_temp)
        from streamlit.testing.v1 import AppTest
    def no_training(*args, **kwargs):
        raise AssertionError("Treinamento durante navegação é proibido")
    monkeypatch.setattr("mindscreen.treinamento.train", no_training)
    monkeypatch.setattr("sklearn.pipeline.Pipeline.fit", no_training)
    app = AppTest.from_file("app/streamlit_app.py", default_timeout=60).run()
    assert not app.exception
    for page in ["Análise exploratória", "Comparação dos modelos", "Explicabilidade"]:
        app.sidebar.radio[0].set_value(page).run(timeout=60)
        assert not app.exception
        assert not app.warning
    app.sidebar.radio[0].set_value("Simulador").run(timeout=60)
    assert not app.exception
    app.button[0].click().run(timeout=60)
    assert not app.exception
    # Duas saídas reais do classificador são exibidas, sem percentuais clínicos.
    assert len(app.metric) == 2
    assert all(metric.value in ["0", "1"] for metric in app.metric)
    manifest, _ = load_dataset("data/processed/manifesto.json")
    rules = json.loads(Path("configs/harmonizacao.json").read_text(encoding="utf-8"))
    default_profile = {"SC_AGE_YEARS": 12, "SCREENTIME": 1, "SC_SEX": 1, "HOURSLEEP": 1, "PHYSACTIV": 1, "MAKEFRIEND": 1}
    expected = predict_profile(default_profile, manifest, rules, REGISTRY)
    displayed = "\n".join(str(m.value) for m in app.markdown)
    for value in expected.values():
        assert f"{value['score']:.4f}" in displayed
    assert [metric.value for metric in app.metric] == [str(v["classe_pesquisa"]) for v in expected.values()]
    assert not any("artefatos desta página" in str(w.value) for w in app.warning)
