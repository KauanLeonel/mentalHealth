"""Análise dos resultados da contribuição, sobre uma execução sintética gravada em pasta temporária."""

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from mindscreen import analise_contribuicao as analise
from mindscreen.contribuicao import run as contribuicao
from test_contribuicao import CONFIG, MANIFEST, sintetico


@pytest.fixture(scope="module")
def resultados(tmp_path_factory):
    root = tmp_path_factory.mktemp("v4")
    config = {**CONFIG, "modelos": {"logistic": {"C": 1.0}, "xgboost": {"n_estimators": 10, "max_depth": 2}}}
    (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
    (root / "manifesto.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    with patch("mindscreen.contribuicao.load_dataset", return_value=(MANIFEST, sintetico(900))):
        contribuicao(root / "manifesto.json", root / "config.json", root / "v4", progresso=lambda m: None)
    pd.DataFrame({"target": ["depressao_atual", "ansiedade_atual"], "modelo": "logistic", "delta_A_menos_B_roc_auc": [0.004, 0.003]}).to_csv(root / "ablation.csv", index=False)
    return root


def test_gera_figuras_tabelas_e_relatorio_sem_ajustar_modelos(resultados, monkeypatch):
    def proibido(*args, **kwargs):
        raise AssertionError("A análise não pode ajustar modelos")
    monkeypatch.setattr("sklearn.pipeline.Pipeline.fit", proibido)
    out = analise.run(resultados / "v4", resultados / "manifesto.json", resultados / "ablation.csv")
    nomes = {p.name for p in out.iterdir()}
    assert {"relatorio.md", "analise.json", "sobreposicao.csv", "consistencia_por_ano.csv", "concordancia_modelos.csv",
            "faixas_etarias.csv", "comparacao_v3.csv", "figuras"} <= nomes
    figuras = {p.stem for p in (out / "figuras").glob("*.json")}
    assert {"depressao_atual_incremental", "ansiedade_atual_isolado", "depressao_atual_por_ano", "perfil_SCREENTIME", "tela_por_ano"} <= figuras
    assert (out / "figuras/plotly.min.js").exists()
    texto = (out / "relatorio.md").read_text(encoding="utf-8")
    for secao in ["## 1. Resposta principal", "## 2. Sobreposição", "## 3. Consistência", "## 4. Robustez", "## 5. Faixas", "## 6. Perfil", "## 7. Comparação", "## Limites"]:
        assert secao in texto
    sobre = pd.read_csv(out / "sobreposicao.csv", encoding="utf-8-sig")
    assert (sobre.fracao_que_permanece - sobre.delta_incremental / sobre.delta_isolado).abs().max() < 1e-12
    long = pd.read_csv(out / "consistencia_por_ano.csv", encoding="utf-8-sig")
    assert len(long) == 2 * 2 * 4 * len(CONFIG["anos"])
    with pytest.raises(FileExistsError):
        analise.run(resultados / "v4", resultados / "manifesto.json")


def test_recusa_resultados_de_outro_dataset(resultados, tmp_path):
    outro = tmp_path / "m.json"
    outro.write_text(json.dumps({"sha256": "diferente"}), encoding="utf-8")
    with pytest.raises(ValueError, match="dataset"):
        analise.carregar(resultados / "v4", outro)


def test_comparacao_v3_e_opcional(resultados):
    contrib = pd.read_csv(resultados / "v4/contribuicoes.csv", encoding="utf-8-sig")
    assert analise.comparar_v3(resultados / "nao_existe.csv", contrib, "SCREENTIME") is None
    v3 = analise.comparar_v3(resultados / "ablation.csv", contrib, "SCREENTIME")
    assert list(v3.target) == ["depressao_atual", "ansiedade_atual"] and v3.delta_v3.tolist() == [0.004, 0.003]
