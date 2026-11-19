"""Fixtures artificiais exclusivas para testar métricas, SHAP e inferência."""

from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from mindscreen.artefatos import read_registry, verified_path
from mindscreen.avaliacao import binary_metrics, choose_threshold, paired_bootstrap, positive_probability
from mindscreen.explicabilidade import class_one_values, explain_pipeline
from mindscreen.inferencia import profile_frame
from mindscreen.treinamento import make_pipeline


def test_metricas_perfeitas_e_desbalanceamento_baseline():
    metrics, curves = binary_metrics([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
    for name in ["roc_auc", "pr_auc", "precision", "recall", "f1", "specificity", "balanced_accuracy"]:
        assert metrics[name] == 1
    assert [metrics[x] for x in ["tn", "fp", "fn", "tp"]] == [2, 0, 0, 2]
    baseline, _ = binary_metrics([0, 0, 0, 1], [0.25] * 4)
    assert baseline["pr_auc"] == 0.25
    assert baseline["roc_auc"] == 0.5
    assert baseline["f1"] == 0
    assert curves["roc"]["x"][0] == 0


@pytest.mark.parametrize("y,scores", [([0, 0], [0.1, 0.2]), ([0.5, 1], [0.1, 0.9]), ([0, 1], [0.1, np.nan]), ([0, 1], [0.1, 2])])
def test_metricas_rejeitam_valores_invalidos(y, scores):
    with pytest.raises(ValueError):
        binary_metrics(y, scores)


def test_classe_positiva_independe_da_ordem_das_classes():
    model = Mock(classes_=np.array([1, 0]))
    model.predict_proba.return_value = np.array([[0.8, 0.2]])
    assert positive_probability(model, [[1]])[0] == 0.8
    values, bases = class_one_values(np.ones((3, 4, 2)), np.ones((3, 2)), [1, 0])
    assert values.shape == (3, 4)
    assert bases.shape == (3,)
    with pytest.raises(ValueError):
        class_one_values(np.ones((3, 4)), np.ones(3), [1, 0])


@pytest.mark.parametrize("name", ["logistic", "random_forest", "xgboost"])
def test_shap_classe_um_aditividade_e_agrupamento(name):
    # Dados inventados apenas como fixture; não representam microdados NSCH.
    X = pd.DataFrame({"idade": np.tile([6, 9, 12, 15, 17, 11], 6), "SCREENTIME": np.tile([1, 2, 3], 12)})
    y = np.tile([0, 0, 1, 0, 1, 1], 6)
    manifest = {"preditores_numericos": ["idade"], "preditores_categoricos": ["SCREENTIME"]}
    model, _ = make_pipeline(manifest, name, {"semente": 42, "n_estimators": 3, "min_samples_leaf": 2})
    model.fit(X, y)
    result = explain_pipeline(model, X.iloc[:12], X.iloc[12:18])
    assert result["features"] == ["idade", "SCREENTIME"]
    assert result["values"].shape == (6, 2)
    assert result["max_erro_aditividade"] < 2e-5
    np.testing.assert_allclose(result["base_values"] + result["values"].sum(axis=1), result["expected"], atol=2e-5)


def test_shap_xgboost_desbalanceado_usa_margem_aditiva():
    # Fixture inventada e desbalanceada: força base_score estimado longe de 0,5, caso em que
    # o modo "probability" do TreeExplainer deixava de ser aditivo com XGBoost 3.x.
    rng = np.random.default_rng(0)
    # Várias categóricas tornam a saída do ColumnTransformer esparsa, como nos dados reais.
    X = pd.DataFrame({"idade": rng.integers(6, 18, 400), "SCREENTIME": rng.integers(1, 6, 400),
                      "SONO": rng.integers(1, 8, 400), "ATIV": rng.integers(1, 5, 400)})
    y = (rng.random(400) < 0.03 + 0.04 * (X.SCREENTIME.to_numpy() - 1)).astype(int)
    manifest = {"preditores_numericos": ["idade"], "preditores_categoricos": ["SCREENTIME", "SONO", "ATIV"]}
    model, _ = make_pipeline(manifest, "xgboost", {"semente": 42, "n_estimators": 20, "min_samples_leaf": 2})
    model.fit(X, y)
    assert hasattr(model.named_steps["preprocess"].transform(X), "tocoo")
    sample = X.iloc[64:128]
    result = explain_pipeline(model, X.iloc[:64], sample)
    assert result["unidade"] == "log-odds da classe 1"
    assert result["fallback"] is None
    assert result["max_erro_aditividade"] < 2e-5
    # A soma SHAP deve reproduzir o modelo como o pipeline o usa (entrada esparsa), não outra função.
    p = positive_probability(model, sample)
    np.testing.assert_allclose(result["base_values"] + result["values"].sum(axis=1), np.log(p / (1 - p)), atol=1e-4)
    assert np.abs(result["values"][:, 1]).sum() > 0


def test_ablation_remove_apenas_screentime():
    manifest = {"preditores_numericos": ["idade"], "preditores_categoricos": ["SCREENTIME", "sexo"]}
    _, a = make_pipeline(manifest, "logistic", {"semente": 42})
    _, b = make_pipeline(manifest, "logistic", {"semente": 42}, without_screen=True)
    assert set(a) - set(b) == {"SCREENTIME"}


def test_formulario_recusa_categorias_e_campos_adicionais():
    manifest = {"preditores_numericos": ["SC_AGE_YEARS"], "preditores_categoricos": ["SCREENTIME"]}
    rules = {"faixa_etaria": [6, 17], "dominios": {"SCREENTIME": [1, 2, 3, 4, 5]}}
    assert profile_frame({"SC_AGE_YEARS": 12, "SCREENTIME": 3}, manifest, rules).shape == (1, 2)
    for profile in [{"SC_AGE_YEARS": 18, "SCREENTIME": 3}, {"SC_AGE_YEARS": 12, "SCREENTIME": 9},
                    {"SC_AGE_YEARS": 12, "SCREENTIME": True}, {"SC_AGE_YEARS": 12, "SCREENTIME": 3, "nome": "fixture"}]:
        with pytest.raises(ValueError):
            profile_frame(profile, manifest, rules)


def test_modelos_fora_da_pasta_autorizada_e_traversal_sao_bloqueados():
    with pytest.raises(ValueError):
        read_registry(Path("data/raw/modelos.json"))
    registry = {"dataset_sha256": "d", "artefatos": {"x": {"arquivo": "../../../nao-confiavel.joblib", "sha256": "x"}}}
    with patch("mindscreen.artefatos.read_registry", return_value=registry), patch("joblib.load") as load:
        with pytest.raises(ValueError):
            verified_path(Path("models/experimentos/registro.json"), "x", "d")
        load.assert_not_called()


def test_limiar_maximiza_f1_e_metricas_o_respeitam():
    y = np.array([0, 0, 0, 0, 1, 1])
    scores = np.array([0.05, 0.1, 0.2, 0.3, 0.25, 0.4])
    threshold, f1 = choose_threshold(y, scores)
    assert threshold == 0.25
    assert f1 == pytest.approx(0.8)
    metrics, _ = binary_metrics(y, scores, threshold=threshold)
    assert metrics["threshold"] == 0.25 and metrics["tp"] == 2 and metrics["fp"] == 1
    assert "pr_auc_trapezoidal" not in metrics
    with pytest.raises(ValueError):
        choose_threshold([0, 0], [0.1, 0.2])


def test_bootstrap_pareado_detecta_diferenca_e_igualdade():
    # Fixture inventada: A ordena perfeitamente; B é ruído.
    rng = np.random.default_rng(1)
    y = np.repeat([0, 1], 200)
    a = y * 0.5 + rng.random(400) * 0.4
    b = rng.random(400)
    ci = paired_bootstrap(y, a, b, n=200, seed=3)
    assert ci["roc_auc_delta_ic_inf"] > 0
    assert ci["roc_auc_A_ic_inf"] <= 1 <= ci["roc_auc_A_ic_sup"] + 1e-12
    same = paired_bootstrap(y, a, a, n=50, seed=3)
    assert same["roc_auc_delta_ic_inf"] == same["roc_auc_delta_ic_sup"] == 0
    assert paired_bootstrap(y, a, b, n=50, seed=3) == paired_bootstrap(y, a, b, n=50, seed=3)
