"""Leitura e validação do conteúdo educativo e dos resultados da pesquisa usados pelo protótipo familiar."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def carregar_conteudo(path=None):
    """Conteúdo educativo de configs/conteudo_familiar.json; toda seção cita fontes declaradas com https."""
    path = Path(path or PROJECT_ROOT / "configs/conteudo_familiar.json")
    conteudo = json.loads(path.read_text(encoding="utf-8"))
    fontes = conteudo.get("fontes", {})
    if not conteudo.get("aviso") or not conteudo.get("secoes"):
        raise ValueError("Conteúdo educativo sem aviso ou seções")
    for nome, fonte in fontes.items():
        if not fonte.get("nome") or not str(fonte.get("url", "")).startswith("https://"):
            raise ValueError(f"Fonte {nome} sem nome ou sem URL https")
    for secao in conteudo["secoes"]:
        if not secao.get("titulo") or not secao.get("itens"):
            raise ValueError("Seção sem título ou itens")
        if any(f not in fontes for f in secao.get("fontes", [])):
            raise ValueError(f"Seção {secao['titulo']} cita fonte não declarada")
    return conteudo


def caminho_resultados_pesquisa(root=PROJECT_ROOT, config_path=None):
    """Pasta da análise de contribuição indicada em configs/interface.json (chave `contribuicao`)."""
    root = Path(root)
    config = json.loads(Path(config_path or root / "configs/interface.json").read_text(encoding="utf-8"))
    folder = (root / config["contribuicao"]).resolve()
    if (root / "reports").resolve() not in folder.parents:
        raise ValueError("Resultados da pesquisa fora de reports/")
    return folder


def carregar_resultados_pesquisa(folder, manifest_path):
    """Resumo, contribuições e perfil de rotina, desde que gerados a partir do dataset do manifesto atual."""
    import pandas as pd
    folder = Path(folder)
    sha = json.loads(Path(manifest_path).read_text(encoding="utf-8"))["sha256"]
    resumo = json.loads((folder / "resumo_familias.json").read_text(encoding="utf-8"))
    if resumo.get("dataset_sha256") != sha:
        raise ValueError("Resultados não correspondem ao dataset atual")
    return {"resumo": resumo,
            "contribuicoes": pd.read_csv(folder / "contribuicoes.csv", encoding="utf-8-sig"),
            "perfil": pd.read_csv(folder / "perfil_rotina.csv", encoding="utf-8-sig", dtype={"periodo": str})}
