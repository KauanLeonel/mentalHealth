"""Contrato explícito para carregar um dataset analítico aprovado."""

import hashlib
import json
from pathlib import Path

TARGETS = ("depressao_atual", "ansiedade_atual")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESERVED = {"ano", "fwc", "stratum", "psu", "fipsst", "hhid", "formtype", "id_registro", *TARGETS}


def safe_output(path):
    output = Path(path).resolve()
    for raw in {(PROJECT_ROOT / "data/raw").resolve(), Path("data/raw").resolve()}:
        if output == raw or raw in output.parents:
            raise ValueError("Não é permitido escrever resultados em data/raw")
    return output


def check_predictors(numeric, categorical):
    predictors = numeric + categorical
    upper = [str(x).upper() for x in predictors]
    if not predictors or len(set(upper)) != len(upper):
        raise ValueError("Preditores vazios ou duplicados")
    if "SCREENTIME" not in upper:
        raise ValueError("SCREENTIME deve ser incluída como preditora")
    if any(x.lower() in RESERVED or x.endswith("_STATUS") or
           x.startswith(("K2Q32", "K2Q33", "DEPRESSAO", "ANSIEDADE", "FWC_")) for x in upper):
        raise ValueError("Preditor proibido: target, componente, gravidade ou variável administrativa")


def load_manifest(path):
    path = Path(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("validado") is not True:
        raise ValueError("Dataset não validado explicitamente no manifesto")
    if not manifest.get("documentacao_validacao") or not manifest.get("aprovado_por"):
        raise ValueError("Manifesto deve identificar documentação e responsável pela validação")
    if type(manifest.get("classe_positiva")) is not int or manifest["classe_positiva"] != 1:
        raise ValueError("Manifesto deve confirmar classe positiva codificada como 1")
    numeric = manifest.get("preditores_numericos", [])
    categorical = manifest.get("preditores_categoricos", [])
    if "preditores_numericos" not in manifest or "preditores_categoricos" not in manifest:
        raise ValueError("Manifesto deve declarar as duas listas de preditores")
    if not isinstance(numeric, list) or not isinstance(categorical, list):
        raise ValueError("Preditores devem ser listas")
    check_predictors(numeric, categorical)
    dataset = (path.parent / manifest["dataset"]).resolve()
    if dataset.suffix.lower() != ".parquet":
        raise ValueError("O dataset analítico deve estar em Parquet")
    digest = hashlib.sha256()
    with dataset.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != manifest.get("sha256", "").lower():
        raise ValueError("SHA-256 do dataset não corresponde ao manifesto")
    return manifest, dataset


def load_dataset(path):
    manifest, dataset = load_manifest(path)
    import pandas as pd
    frame = pd.read_parquet(dataset)
    required = {"ano", "FWC", "STRATUM", *TARGETS, *manifest["preditores_numericos"], *manifest["preditores_categoricos"]}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")
    if frame["ano"].isna().any() or not frame["ano"].isin([2020, 2021, 2022, 2023, 2024]).all():
        raise ValueError("Ano inválido ou ausente")
    return manifest, frame
