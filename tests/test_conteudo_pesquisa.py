"""Conteúdo educativo, leitura dos resultados da pesquisa e gráficos do protótipo."""

import json

import pandas as pd
import pytest

from mindscreen.conteudo import caminho_resultados_pesquisa, carregar_conteudo, carregar_resultados_pesquisa
from mindscreen.painel import contribution_chart, routine_history_chart, routine_profile_chart
from mindscreen.rotina import historico


def test_conteudo_real_cita_fontes_e_orienta_procura_de_profissional():
    conteudo = carregar_conteudo()
    titulos = [s["titulo"] for s in conteudo["secoes"]]
    assert "Quando conversar com um profissional" in titulos
    texto = json.dumps(conteudo, ensure_ascii=False)
    assert "188" in texto and "192" in texto
    assert all(f["url"].startswith("https://") for f in conteudo["fontes"].values())


def test_conteudo_recusa_fonte_nao_declarada(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"aviso": "a", "secoes": [{"titulo": "t", "itens": ["i"], "fontes": ["x"]}], "fontes": {}}), encoding="utf-8")
    with pytest.raises(ValueError):
        carregar_conteudo(path)


def test_resultados_exigem_mesmo_dataset_e_pasta_em_reports(tmp_path):
    (tmp_path / "reports/r").mkdir(parents=True)
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/interface.json").write_text(json.dumps({"contribuicao": "reports/r"}), encoding="utf-8")
    folder = caminho_resultados_pesquisa(tmp_path)
    (folder / "resumo_familias.json").write_text(json.dumps({"dataset_sha256": "abc"}), encoding="utf-8")
    pd.DataFrame({"a": [1]}).to_csv(folder / "contribuicoes.csv", index=False)
    pd.DataFrame({"periodo": ["2020–2024"]}).to_csv(folder / "perfil_rotina.csv", index=False)
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"sha256": "abc"}), encoding="utf-8")
    assert carregar_resultados_pesquisa(folder, manifest)["resumo"]["dataset_sha256"] == "abc"
    manifest.write_text(json.dumps({"sha256": "outro"}), encoding="utf-8")
    with pytest.raises(ValueError):
        carregar_resultados_pesquisa(folder, manifest)
    (tmp_path / "configs/interface.json").write_text(json.dumps({"contribuicao": "../fora"}), encoding="utf-8")
    with pytest.raises(ValueError):
        caminho_resultados_pesquisa(tmp_path)


def test_graficos_de_contribuicao_perfil_e_historico():
    contrib = pd.DataFrame({"target": "depressao_atual", "modelo": "logistic", "tipo": "incremental", "fator": ["SCREENTIME", "HOURSLEEP"],
                            "delta_auc": [0.004, 0.02], "delta_auc_ic_inf": [0.002, 0.015], "delta_auc_ic_sup": [0.006, 0.025]})
    figure = contribution_chart(contrib, "depressao_atual", "logistic")
    assert list(figure.data[0].y) == ["Tempo de tela", "Sono"]
    with pytest.raises(ValueError):
        contribution_chart(contrib, "ansiedade_atual", "logistic")
    perfil = pd.DataFrame({"variavel": "SCREENTIME", "periodo": "2020–2024", "faixa_etaria": ["6–11", "12–17"], "categoria": [1, 1],
                           "rotulo_categoria": "Menos de 1 hora", "percentual_ponderado": [20.0, 10.0]})
    assert len(routine_profile_chart(perfil, "SCREENTIME").data) == 2
    frame = historico([{"data": "2024-01-01", "tela_horas": 2.0, "sono_horas": None, "atividades": []}])
    figure = routine_history_chart(frame, [{"tipo": "tela_max", "valor": 2.0, "descricao": "Até 2 h"}])
    assert len(figure.data) == 1 and len(figure.layout.shapes) == 1
