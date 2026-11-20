"""Calibração com dados sintéticos (fixtures inventadas; não representam microdados NSCH)."""

from io import BytesIO

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import StratifiedKFold

from mindscreen.avaliacao import calibration_metrics, choose_threshold, positive_probability
from mindscreen.calibracao import Calibrador, ModeloCalibrado, calibrate_scores, cross_fitted
from mindscreen.explicabilidade import explain_pipeline
from mindscreen.treinamento import make_pipeline


def scores_inflados(n=4000, seed=0):
    """Probabilidade verdadeira p; pontuação inflada como num modelo com class_weight balanceado."""
    rng = np.random.default_rng(seed)
    p = rng.beta(1, 9, n)
    y = (rng.random(n) < p).astype(int)
    inflated = 1 / (1 + np.exp(-(np.log(p / (1 - p)) + 2.0)))
    return y, p, inflated


def test_metricas_de_calibracao_distinguem_calibrado_de_inflado():
    y, p, inflated = scores_inflados()
    good, curve = calibration_metrics(y, p)
    bad, _ = calibration_metrics(y, inflated)
    assert abs(good["diferenca_media"]) < 0.02
    assert abs(good["inclinacao_cox"] - 1) < 0.2 and abs(good["intercepto_cox"]) < 0.3
    assert good["ece"] < 0.03 < bad["ece"]
    assert bad["diferenca_media"] > 0.1 and bad["brier"] > good["brier"]
    assert bad["brier_skill"] < good["brier_skill"]
    assert sum(curve["n"]) == len(y) and good["bins"] == 10


def test_metricas_de_calibracao_com_pontuacao_constante():
    metrics, curve = calibration_metrics([0, 0, 0, 1], [0.25] * 4)
    assert metrics["bins"] == 1 and curve["n"] == [4]
    assert metrics["brier_skill"] == pytest.approx(0)
    assert np.isnan(metrics["inclinacao_cox"])


@pytest.mark.parametrize("y,scores", [([0, 0], [0.1, 0.2]), ([0, 1], [0.1, 1.5]), ([0, 1, 1], [0.1, 0.2])])
def test_metricas_de_calibracao_rejeitam_entradas_invalidas(y, scores):
    with pytest.raises(ValueError):
        calibration_metrics(y, scores)


@pytest.mark.parametrize("metodo", ["sigmoide", "isotonica"])
def test_calibrador_e_monotonico_e_corrige_inflacao(metodo):
    y, _, inflated = scores_inflados()
    calibrated = Calibrador(metodo).fit(inflated, y).transform(inflated)
    order = np.argsort(inflated)
    assert np.all(np.diff(calibrated[order]) >= -1e-12)
    assert np.all((calibrated >= 0) & (calibrated <= 1))
    assert calibration_metrics(y, calibrated)[0]["ece"] < calibration_metrics(y, inflated)[0]["ece"]


def test_calibrador_rejeita_metodo_desconhecido_e_uso_sem_ajuste():
    with pytest.raises(ValueError):
        Calibrador("beta")
    with pytest.raises(ValueError):
        Calibrador("isotonica").transform([0.2])


def test_calibracao_cruzada_nao_usa_o_proprio_fold():
    y = np.array([0, 1] * 20)
    scores = np.linspace(0.05, 0.95, 40)
    splits = list(StratifiedKFold(5, shuffle=True, random_state=0).split(scores, y))
    seen = []
    original = Calibrador.fit

    def spy(self, s, target):
        seen.append(set(np.round(s, 10)))
        return original(self, s, target)

    Calibrador.fit = spy
    try:
        cross_fitted(scores, y, splits, "isotonica")
    finally:
        Calibrador.fit = original
    for (_, test_idx), fitted_on in zip(splits, seen):
        assert not set(np.round(scores[test_idx], 10)) & fitted_on


def test_escolha_do_metodo_e_do_limiar_usa_so_desenvolvimento():
    y, _, inflated = scores_inflados()
    splits = list(StratifiedKFold(5, shuffle=True, random_state=1).split(inflated, y))
    result = calibrate_scores(inflated, y, splits)
    assert result["metodo"] in {"sigmoide", "isotonica"}
    assert set(result["metricas_cv"]) == {"nenhum", "sigmoide", "isotonica"}
    best = min(result["metricas_cv"].values(), key=lambda m: m["brier"])
    assert result["metricas_cv"][result["metodo"]] == best
    assert 0 < result["limiar"] < 1 and result["f1_oof"] > 0
    with pytest.raises(ValueError):
        calibrate_scores(inflated, y, splits, criterio="roc_auc")


def test_sem_calibracao_vence_quando_ja_calibrado():
    y, p, _ = scores_inflados(seed=3)
    splits = list(StratifiedKFold(5, shuffle=True, random_state=1).split(p, y))
    result = calibrate_scores(p, y, splits, metodos=("nenhum",))
    assert result["metodo"] == "nenhum"
    assert result["limiar"] == pytest.approx(choose_threshold(y, p)[0])


@pytest.mark.parametrize("name", ["logistic", "xgboost"])
def test_modelo_calibrado_preserva_contrato_ordenacao_e_shap(name):
    X = pd.DataFrame({"idade": np.tile([6, 9, 12, 15, 17, 11], 10), "SCREENTIME": np.tile([1, 2, 3], 20)})
    y = np.tile([0, 0, 1, 0, 1, 1], 10)
    manifest = {"preditores_numericos": ["idade"], "preditores_categoricos": ["SCREENTIME"]}
    base, _ = make_pipeline(manifest, name, {"semente": 42, "n_estimators": 3, "min_samples_leaf": 2})
    base.fit(X, y)
    raw = positive_probability(base, X)
    model = ModeloCalibrado(base, Calibrador("sigmoide").fit(raw, y))
    buffer = BytesIO()
    joblib.dump(model, buffer)
    buffer.seek(0)
    model = joblib.load(buffer)
    proba = model.predict_proba(X)
    assert list(model.feature_names_in_) == ["idade", "SCREENTIME"] and set(model.classes_) == {0, 1}
    np.testing.assert_allclose(proba.sum(axis=1), 1)
    calibrated = positive_probability(model, X)
    assert np.all(np.diff(calibrated[np.argsort(raw, kind="stable")]) >= -1e-12)
    assert explain_pipeline(model, X.iloc[:12], X.iloc[12:18])["max_erro_aditividade"] < 2e-5


def test_interface_le_caminhos_da_configuracao_e_restringe_pastas(tmp_path):
    import json
    from mindscreen.painel import interface_paths
    (tmp_path / "configs").mkdir()
    config = tmp_path / "configs/interface.json"
    config.write_text(json.dumps({"registro": "models/x/registro.json", "relatorios": "reports/v3"}), encoding="utf-8")
    paths = interface_paths(tmp_path)
    assert paths["registro"] == (tmp_path / "models/x/registro.json").resolve()
    assert paths["relatorios"] == (tmp_path / "reports/v3").resolve()
    for bad in ({"registro": "../fora/registro.json", "relatorios": "reports"}, {"registro": "models/x/registro.json", "relatorios": "data/raw"}):
        config.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(ValueError):
            interface_paths(tmp_path)


def test_secao_de_calibracao_do_relatorio(tmp_path):
    from mindscreen.resultados import calibration_lines, render_calibration_figures
    evaluation = {"selecao": {"A/depressao_atual": "A/depressao_atual_xgboost", "A/ansiedade_atual": "A/ansiedade_atual_logistic"}}
    cv, test, curves = [], [], {}
    for target in ("depressao_atual", "ansiedade_atual"):
        for name in ("logistic", "random_forest", "xgboost"):
            for metodo in ("nenhum", "isotonica"):
                cv.append({"experimento": "A", "target": target, "modelo": name, "metodo": metodo, "escolhido": metodo == "isotonica", "brier": 0.1})
            for versao, brier in (("sem_calibracao", 0.17), ("calibrado", 0.05)):
                test.append({"experimento": "A", "target": target, "modelo": name, "versao": versao, "brier": brier, "brier_prevalencia": 0.06,
                             "brier_skill": 1 - brier / 0.06, "media_prevista": 0.3, "prevalencia_observada": 0.07, "ece": 0.2, "inclinacao_cox": 1.0})
                curves[f"A/{target}_{name}/{versao}"] = {"media_prevista": [0.1, 0.5], "frequencia_observada": [0.05, 0.2], "n": [10, 10]}
    calibration = {"cv": cv, "teste": test, "curvas": curves, "bins": 10}
    text = "\n".join(calibration_lines(calibration, evaluation))
    assert "xgboost ★ (método isotonica): Brier 0.1700 → 0.0500" in text
    assert "logistic ★" in text and "não orientaram nenhuma escolha" in text
    render_calibration_figures(calibration, evaluation, tmp_path)
    assert (tmp_path / "depressao_atual_calibracao.json").exists() and (tmp_path / "ansiedade_atual_calibracao.json").exists()


def test_artefato_calibrado_nao_depende_de_main():
    # Regressão: executar a calibração com `python -m` gravava `__main__.ModeloCalibrado`,
    # que não pode ser carregado por outro processo.
    import pickle
    model = ModeloCalibrado(None, Calibrador("nenhum"))
    payload = pickle.dumps(model)
    assert b"__main__" not in payload and b"mindscreen.modelo_calibrado" in payload
