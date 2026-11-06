"""Contrato do simulador: valida categorias e utiliza o pipeline persistido inteiro."""

from pathlib import Path

import pandas as pd

from mindscreen.artefatos import load_model, read_registry
from mindscreen.avaliacao import positive_probability
from mindscreen.dados_validados import TARGETS


def profile_frame(profile, manifest, rules):
    features = manifest["preditores_numericos"] + manifest["preditores_categoricos"]
    if set(profile) != set(features):
        raise ValueError("O formulário não corresponde às variáveis aprovadas")
    normalized = {}
    for name in features:
        value = profile[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not float(value).is_integer():
            raise ValueError("Informe categorias inteiras válidas")
        if name == "SC_AGE_YEARS":
            if not rules["faixa_etaria"][0] <= value <= rules["faixa_etaria"][1]:
                raise ValueError("Faixa etária incompatível com o estudo")
        elif value not in rules["dominios"][name]:
            raise ValueError("Categoria incompatível com o questionário")
        normalized[name] = int(value)
    return pd.DataFrame([normalized], columns=features)


def predict_profile(profile, manifest, rules, registry_path=Path("models/experimentos/registro.json")):
    X = profile_frame(profile, manifest, rules)
    registry = read_registry(registry_path)
    result = {}
    for target in TARGETS:
        key = registry["selecionados"]["A/" + target]
        model = load_model(registry_path, key, manifest["sha256"])
        score = float(positive_probability(model, X)[0])
        result[target] = {"classe_pesquisa": int(score >= 0.5), "score": score, "calibrado": bool(registry["calibrado"]),
                          "modelo": registry["artefatos"][key]["algoritmo"], "classe_positiva": 1}
    return result
