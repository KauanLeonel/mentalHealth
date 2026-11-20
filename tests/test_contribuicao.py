"""Análise de contribuição incremental com dados sintéticos; nenhum microdado real é usado."""

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")
from sklearn.metrics import roc_auc_score

from mindscreen.contribuicao import (auc_ponderada, bootstrap_delta, comparacoes, conjuntos, run,
                                     validar_config)
from mindscreen.treinamento import make_pipeline

MANIFEST = {"preditores_numericos": ["SC_AGE_YEARS"], "preditores_categoricos": ["SCREENTIME", "SC_SEX", "HOURSLEEP", "PHYSACTIV", "MAKEFRIEND"],
            "sha256": "sintetico", "rotulos": {"SCREENTIME": {"1": "Menos de 1 hora", "2": "1 hora"}}}
CONFIG = {"semente": 1, "anos": [2020, 2021, 2022], "base": ["SC_AGE_YEARS", "SC_SEX"],
          "fatores_rotina": ["SCREENTIME", "HOURSLEEP", "PHYSACTIV", "MAKEFRIEND"], "fator_foco": "SCREENTIME",
          "modelo_principal": "logistic", "modelos": {"logistic": {"C": 1.0}}, "bootstrap": 20, "nivel_confianca": 0.95,
          "peso_amostral": "FWC", "peso_descritivo_periodo": "FWC_media_anual_periodo", "faixas_etarias": {"6–11": [6, 11], "12–17": [12, 17]}}


def sintetico(n=600, seed=0):
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame({"ano": rng.choice(CONFIG["anos"], n), "SC_AGE_YEARS": rng.integers(6, 18, n),
                          "SC_SEX": rng.integers(1, 3, n), "SCREENTIME": rng.integers(1, 6, n), "HOURSLEEP": rng.integers(1, 8, n),
                          "PHYSACTIV": rng.integers(1, 5, n), "MAKEFRIEND": rng.integers(1, 4, n), "FWC": rng.uniform(10, 100, n), "STRATUM": "1"})
    frame["FWC_media_anual_periodo"] = frame.FWC / 3
    logit = -2 + 0.8 * (frame.MAKEFRIEND - 1) + 0.2 * (frame.SC_AGE_YEARS - 12) / 3
    frame["depressao_atual"] = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)
    frame["ansiedade_atual"] = (rng.uniform(size=n) < 1 / (1 + np.exp(-(logit + 0.5)))).astype(int)
    frame.loc[0, "SCREENTIME"] = None
    frame.loc[1, "depressao_atual"] = None
    return frame


def test_auc_ponderada_coincide_com_sklearn_inclusive_empates():
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 300)
    scores = np.round(rng.uniform(size=300), 1)
    weights = rng.uniform(0.1, 5, 300)
    assert auc_ponderada(y, scores) == pytest.approx(roc_auc_score(y, scores))
    assert auc_ponderada(y, scores, weights) == pytest.approx(roc_auc_score(y, scores, sample_weight=weights))
    assert np.isnan(auc_ponderada([1, 1], [0.2, 0.3]))


def test_bootstrap_pareado_reflete_diferenca_e_e_reprodutivel():
    rng = np.random.default_rng(4)
    y = rng.integers(0, 2, 400)
    bom = y + rng.normal(0, 0.5, 400)
    ruido = rng.normal(0, 1, 400)
    a = bootstrap_delta(y, bom, ruido, estratos=rng.integers(0, 2, 400), n=50, seed=9)
    b = bootstrap_delta(y, bom, ruido, estratos=None, n=50, seed=9)
    assert a["ic_inf"] > 0 and a["prop_delta_positivo"] == 1.0
    assert a["reamostras_validas"] == 50
    assert bootstrap_delta(y, bom, bom, n=10)["ic_sup"] == 0


def test_conjuntos_avaliam_todos_os_fatores_do_mesmo_modo():
    sets = conjuntos(CONFIG)
    assert sets["rotina_completa"] == ["SC_AGE_YEARS", "SC_SEX", "SCREENTIME", "HOURSLEEP", "PHYSACTIV", "MAKEFRIEND"]
    assert "SCREENTIME" not in sets["rotina_completa-SCREENTIME"]
    comps = comparacoes(CONFIG)
    assert len(comps) == 8 and {c["fator"] for c in comps} == set(CONFIG["fatores_rotina"])
    assert all(set(sets[c["com"]]) - set(sets[c["sem"]]) == {c["fator"]} for c in comps)


def test_config_recusa_preditor_fora_do_manifesto_ou_faltante():
    validar_config(CONFIG, MANIFEST)
    with pytest.raises(ValueError):
        validar_config({**CONFIG, "fatores_rotina": ["SCREENTIME", "HOURSLEEP", "PHYSACTIV"]}, MANIFEST)
    with pytest.raises(ValueError):
        validar_config({**CONFIG, "base": ["SC_AGE_YEARS", "SC_SEX", "depressao_atual"]}, MANIFEST)
    with pytest.raises(ValueError):
        make_pipeline(MANIFEST, "logistic", CONFIG, predictors=["K2Q32A"])


def test_execucao_completa_gera_resultados_e_resumo_sem_salvar_modelos():
    frame = sintetico()
    written = {}

    def capture(path, content, **kwargs):
        written[Path(path).name] = content

    def capture_csv(self, path, **kwargs):
        written[Path(path).name] = self.copy()

    with patch("mindscreen.contribuicao.load_dataset", return_value=(MANIFEST, frame)), \
         patch("mindscreen.contribuicao.version", return_value="fixture"), \
         patch("pathlib.Path.read_text", return_value=json.dumps(CONFIG)), \
         patch("pathlib.Path.exists", return_value=False), patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.write_text", new=capture), patch.object(pd.DataFrame, "to_csv", new=capture_csv):
        payload = run(Path("manifesto"), Path("config"), Path("reports/modelagem/fixture-nao-gravada"), progresso=lambda m: None)

    assert set(written) == {"metricas.csv", "contribuicoes.csv", "perfil_rotina.csv", "contribuicao.json", "resumo_familias.json", "interpretacao.md"}
    assert not any(name.endswith(".joblib") for name in written)
    contrib = written["contribuicoes.csv"]
    assert len(contrib) == 2 * 8
    # A amizade gera os dados sintéticos; o tempo de tela não. A análise deve refletir isso.
    inc = contrib.loc[contrib.tipo.eq("incremental") & contrib.target.eq("depressao_atual")].set_index("fator")
    assert inc.loc["MAKEFRIEND", "delta_auc"] > inc.loc["SCREENTIME", "delta_auc"]
    assert inc.loc["MAKEFRIEND", "delta_auc_ic_inf"] > 0
    assert payload["populacao"]["depressao_atual"]["excluidos_target_ausente"] == 1
    metrics = written["metricas.csv"]
    assert set(metrics.ano_avaliado) == {2020, 2021, 2022, "todos"}
    perfil = written["perfil_rotina.csv"]
    soma = perfil.loc[perfil.periodo.eq("2020–2024")].groupby(["variavel", "faixa_etaria"]).percentual_ponderado.sum()
    assert np.allclose(soma, 100)
    resumo = json.loads(written["resumo_familias.json"])
    assert resumo["dataset_sha256"] == "sintetico"
    assert len(resumo["blocos"]) == 2 and all(len(b["frases"]) == 5 for b in resumo["blocos"])
    assert all("diagnóstico" not in f.lower() for b in resumo["blocos"] for f in b["frases"])


def test_barra_de_progresso_conta_etapas_e_estima_tempo():
    from io import StringIO
    from mindscreen.contribuicao import BarraProgresso, total_etapas
    assert total_etapas(CONFIG) == 2 * 1 * (10 + 8)
    tempos = iter([0, 0, 10, 20, 30])
    stream = StringIO()
    barra = BarraProgresso(stream=stream, largura=10, relogio=lambda: next(tempos))
    barra.definir_total(4)
    barra("etapa 1")
    barra("etapa 2")
    assert "1/4" in stream.getvalue().split("\r")[-1] and "restante ~0:00:30" in stream.getvalue().split("\r")[-1]
    barra("etapa 3")
    barra.concluir()
    final = stream.getvalue().split("\r")[-1]
    assert final.startswith("[##########] 4/4") and final.endswith("\n")


def test_run_informa_total_e_todas_as_etapas_a_barra():
    calls = []

    class Coletor:
        def definir_total(self, total):
            calls.append(("total", total))

        def __call__(self, mensagem):
            calls.append(mensagem)

    with patch("mindscreen.contribuicao.load_dataset", return_value=(MANIFEST, sintetico(300))), \
         patch("mindscreen.contribuicao.version", return_value="fixture"), \
         patch("pathlib.Path.read_text", return_value=json.dumps(CONFIG)), patch("pathlib.Path.exists", return_value=False), \
         patch("pathlib.Path.mkdir"), patch("pathlib.Path.write_text"), patch.object(pd.DataFrame, "to_csv"):
        run(Path("manifesto"), Path("config"), Path("reports/modelagem/fixture-nao-gravada"), progresso=Coletor())
    assert calls[0] == ("total", 36) and len(calls) - 1 == 36


def test_recusa_sobrescrever_resultados():
    with patch("mindscreen.contribuicao.load_dataset", return_value=(MANIFEST, sintetico(60))), \
         patch("pathlib.Path.read_text", return_value=json.dumps(CONFIG)), patch("pathlib.Path.exists", return_value=True):
        with pytest.raises(FileExistsError):
            run(Path("manifesto"), Path("config"), Path("reports/modelagem/existente"))
