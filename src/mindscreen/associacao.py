"""Odds ratios ajustados descritivos da amostra, sem inferência populacional."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder

from mindscreen.dados_validados import TARGETS, load_dataset, safe_output


def run(manifest_path, output):
    manifest, frame = load_dataset(manifest_path)
    output = safe_output(output)
    output.mkdir(parents=True, exist_ok=True)
    # Covariáveis definidas antes de observar o teste, incluindo ano para ajuste temporal.
    categories = ["SCREENTIME", "SC_SEX", "HOURSLEEP", "PHYSACTIV", "MAKEFRIEND", "ano"]
    continuous = ["SC_AGE_YEARS"]
    results, details = [], {}
    for target in TARGETS:
        development = frame.loc[frame.ano.lt(2024)]
        complete = development.dropna(subset=[*categories, *continuous, target]).copy()
        if not set(complete[target].unique()) == {0, 1}:
            raise ValueError("Casos completos não contêm ambas as classes")
        encoder = OneHotEncoder(drop="first", sparse_output=False, handle_unknown="error")
        Z = encoder.fit_transform(complete[categories])
        if encoder.categories_[0][0] != 1:
            raise ValueError("Categoria de referência SCREENTIME=1 ausente nos casos completos")
        design = np.column_stack([complete[continuous].astype(float).to_numpy(), Z])
        model = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=3000, tol=1e-8)
        model.fit(design, complete[target].astype(int))
        if model.n_iter_[0] >= model.max_iter:
            raise ValueError("A regressão de associação não convergiu")
        names = [*continuous, *encoder.get_feature_names_out(categories)]
        for index, name in enumerate(names):
            if name.startswith("SCREENTIME_"):
                code = int(float(name.split("_", 1)[1]))
                results.append({"target": target, "categoria_screentime": code,
                                "referencia": int(encoder.categories_[0][0]), "coef_log_odds": float(model.coef_[0, index]),
                                "odds_ratio_ajustada_amostral": float(np.exp(model.coef_[0, index])), "n_casos_completos": len(complete)})
        details[target] = {"n_desenvolvimento": len(development), "n_completos": len(complete),
                           "excluidos_ausencia_target_ou_covariavel": len(development) - len(complete),
                           "covariaveis": categories[1:] + continuous, "anos": [2020, 2021, 2022, 2023],
                           "penalizacao": None, "pesos": False, "intervalos_confianca": None}
    table = pd.DataFrame(results)
    table.to_csv(output / "odds_ratios.csv", index=False, encoding="utf-8-sig")
    payload = {"dataset_sha256": manifest["sha256"], "odds_ratios": results, "detalhes": details,
               "interpretacao": "OR condicional da amostra em casos completos, sem pesos, erros padrão ou IC. Categoria de referência: menos de 1 hora. Ajuste simultâneo por idade, sexo, sono, atividade física, amizade e ano. Não estima risco relativo, efeito causal ou inferência para população. Covariáveis contemporâneas podem ser mediadoras ou consequências do desfecho; o ajuste não elimina confundimento."}
    (output / "associacao.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
