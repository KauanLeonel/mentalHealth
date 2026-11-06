"""Treinamento somente em 2020–2023; 2024 é mantido intocado."""

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
from inspect import signature
import json
from pathlib import Path

from mindscreen.dados_validados import TARGETS, load_dataset, safe_output


def categorical_text(frame):
    """Normaliza tipos dentro do pipeline, preservando ausências para imputação."""
    return frame.astype("string").astype(object).where(frame.notna(), None)


def make_pipeline(manifest, name, config, without_screen=False):
    """Constrói pipeline independente; sem ajustes fora dos folds."""
    from sklearn.compose import ColumnTransformer
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
    from xgboost import XGBClassifier
    numeric = [c for c in manifest["preditores_numericos"] if not (without_screen and c == "SCREENTIME")]
    categorical = [c for c in manifest["preditores_categoricos"] if not (without_screen and c == "SCREENTIME")]
    transforms = []
    if numeric:
        steps = [("impute", SimpleImputer(strategy="median", keep_empty_features=True))]
        if name == "logistic":
            steps.append(("scale", StandardScaler()))
        transforms.append(("numericas", Pipeline(steps), numeric))
    if categorical:
        steps = [("text", FunctionTransformer(categorical_text, validate=False, feature_names_out="one-to-one")),
                 ("impute", SimpleImputer(missing_values=None, strategy="constant", fill_value="__AUSENTE__", keep_empty_features=True)),
                 ("encode", OneHotEncoder(handle_unknown="ignore"))]
        transforms.append(("categoricas", Pipeline(steps), categorical))
    seed = config["semente"]
    models = {"dummy": DummyClassifier(strategy="prior"),
              "logistic": LogisticRegression(max_iter=2000, random_state=seed),
              "random_forest": RandomForestClassifier(n_estimators=config.get("n_estimators", 200), min_samples_leaf=config.get("min_samples_leaf", 10), random_state=seed, n_jobs=1),
              "xgboost": XGBClassifier(n_estimators=config.get("n_estimators", 200), objective="binary:logistic", eval_metric="logloss", random_state=seed, n_jobs=1)}
    return Pipeline([("preprocess", ColumnTransformer(transforms)), ("model", models[name])]), numeric + categorical


def train(manifest_path, config_path, output, without_screen=False):
    manifest, frame = load_dataset(manifest_path)
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if config["ano_teste"] != 2024 or config["anos_desenvolvimento"] != [2020, 2021, 2022, 2023]:
        raise ValueError("A divisão temporal deve manter 2024 para teste e 2020–2023 para desenvolvimento")
    if config["folds"] != 5:
        raise ValueError("A validação exige 5 folds")
    if not (frame["ano"] == 2024).any():
        raise ValueError("O conjunto temporal de 2024 não está disponível")
    dev = frame.loc[frame["ano"].isin(config["anos_desenvolvimento"])].copy()
    if set(dev["ano"].unique()) != set(config["anos_desenvolvimento"]):
        raise ValueError("Faltam anos de desenvolvimento")
    import joblib
    from sklearn.model_selection import GridSearchCV, StratifiedKFold

    numeric = [c for c in manifest["preditores_numericos"] if not (without_screen and c == "SCREENTIME")]
    categorical = [c for c in manifest["preditores_categoricos"] if not (without_screen and c == "SCREENTIME")]
    features = [c for c in numeric + categorical if not (without_screen and c == "SCREENTIME")]
    seed = config["semente"]
    output = safe_output(output)
    artifact_names = [f"{target}_{name}.joblib" for target in TARGETS for name in ("dummy", "logistic", "random_forest", "xgboost")]
    artifact_names.append("treinamento.json")
    if any((output / name).exists() for name in artifact_names):
        raise FileExistsError("Já existem artefatos no destino; escolha outra pasta para preservar os resultados anteriores")
    output.mkdir(parents=True, exist_ok=True)
    log = {"data_utc": datetime.now(timezone.utc).isoformat(), "configuracao": config,
           "manifesto": str(Path(manifest_path)), "sha256_dataset": manifest["sha256"],
           "preditores": features, "positive_class": 1, "experimento": "B_sem_SCREENTIME" if without_screen else "A_com_SCREENTIME",
           "peso_treinamento": "Não utilizado: decisão inicial uniforme entre estimadores; os pesos permanecem no dataset de entrada. Não constitui inferência para desenho complexo.",
           "seleção": "ROC AUC média em validação cruzada de desenvolvimento; 2024 não avaliado.",
           "versoes": {p: version(p) for p in ("pandas", "numpy", "scikit-learn", "xgboost", "joblib", "pyarrow")}, "resultados": {}}
    for target in TARGETS:
        y = dev[target].dropna()
        if not y.isin([0, 1]).all() or set(y.unique()) != {0, 1} or y.value_counts().min() < 5:
            raise ValueError(f"{target}: classes 0 e 1 e pelo menos 5 registros por classe são necessários")
    for target in TARGETS:
        subset = dev.loc[dev[target].notna()]
        y = subset[target]
        X = subset[features].copy()
        if numeric and X[numeric].isna().all().any():
            raise ValueError("Preditor numérico inteiramente ausente no desenvolvimento")
        log["resultados"][target] = {"registros": len(y), "excluidos_target_ausente": len(dev) - len(y), "classes": {str(k): int(v) for k, v in y.value_counts().items()}, "modelos": {}}
        for name in ("dummy", "logistic", "random_forest", "xgboost"):
            pipe, _ = make_pipeline(manifest, name, config, without_screen)
            estimator = pipe.named_steps["model"]
            print(f"{target} / {name} / {'B' if without_screen else 'A'}: validação cruzada", flush=True)
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
            search = GridSearchCV(pipe, config["busca"].get(name, {}), cv=cv, scoring="roc_auc", n_jobs=config["n_jobs"], error_score="raise", refit=True)
            search.fit(X, y)
            joblib.dump(search.best_estimator_, output / f"{target}_{name}.joblib")
            log["resultados"][target]["modelos"][name] = {"melhores_parametros": search.best_params_, "roc_auc_cv": float(search.best_score_),
                                                          "fit_aceita_sample_weight": "sample_weight" in signature(estimator.fit).parameters,
                                                          "sample_weight_utilizado": False}
            print(f"  ROC AUC CV: {search.best_score_:.6f}", flush=True)
        scores = log["resultados"][target]["modelos"]
        log["resultados"][target]["selecionado_por_cv"] = max(scores, key=lambda name: scores[name]["roc_auc_cv"])
    (output / "treinamento.json").write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/treinamento.json"))
    parser.add_argument("--output", type=Path, default=Path("models/treinamento"))
    parser.add_argument("--sem-screentime", action="store_true")
    args = parser.parse_args()
    try:
        train(args.manifesto, args.config, args.output, args.sem_screentime)
    except (FileNotFoundError, FileExistsError, ValueError, ImportError) as exc:
        parser.exit(1, f"Treinamento não executado: {exc}\n")
    print(f"Modelos e log salvos em {args.output}")


if __name__ == "__main__":
    main()
