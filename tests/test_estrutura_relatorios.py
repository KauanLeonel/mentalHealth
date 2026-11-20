"""Padronização de reports/: estrutura das versões de modelagem e proteção da versão 2."""

import json
from pathlib import Path

import pytest

from mindscreen import analises

ROOT = Path(__file__).resolve().parents[1]
MODELAGEM = ROOT / "reports" / "modelagem"
SUBPASTAS = {"avaliacao", "associacao", "figuras", "resultados"}


def versoes():
    if not MODELAGEM.exists():
        return []
    return sorted(p for p in MODELAGEM.iterdir() if p.is_dir() and not p.name.startswith("_"))


@pytest.mark.parametrize("versao", versoes(), ids=lambda p: p.name)
def test_versao_tem_estrutura_padrao(versao):
    presentes = {p.name for p in versao.iterdir() if p.is_dir()}
    assert SUBPASTAS <= presentes
    assert presentes - SUBPASTAS <= {"calibracao"}
    assert (versao / "avaliacao/avaliacao.json").exists()
    assert (versao / "resultados/resumo.json").exists()


def test_nenhum_relatorio_de_modelagem_solto_na_raiz():
    raiz = ROOT / "reports"
    if not raiz.exists():
        pytest.skip("reports/ ausente")
    soltos = {"avaliacao", "associacao", "figures", "figuras", "resultados"} & {p.name for p in raiz.iterdir()}
    assert not soltos


def test_interface_aponta_para_versao_existente():
    config = json.loads((ROOT / "configs/interface.json").read_text(encoding="utf-8"))
    relatorios = (ROOT / config["relatorios"]).resolve()
    assert relatorios.parent == MODELAGEM.resolve()


@pytest.mark.parametrize("destino", [analises.REPORTS_ROOT, analises.REPORTS_V2])
def test_calibrados_nao_sobrescrevem_raiz_nem_v2(destino, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="pasta própria"):
        analises.run("manifesto.json", "config.json", "models/x", destino, calibration=tmp_path)
