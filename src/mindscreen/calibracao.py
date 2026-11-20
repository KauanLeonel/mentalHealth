"""Calibração pós-hoc das pontuações com previsões fora do fold de 2020–2023.

Os pipelines já treinados (busca de hiperparâmetros congelada) recebem um calibrador
monotônico ajustado nas previsões fora do fold do desenvolvimento, nos mesmos cinco
folds do treinamento. O método (nenhum, sigmoide ou isotônica) e o limiar são escolhidos
apenas em 2020–2023; 2024 só é usado depois, para descrever o resultado.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mindscreen.artefatos import MODELS_ROOT, load_model, read_registry
from mindscreen.avaliacao import calibration_metrics, choose_threshold, positive_probability
from mindscreen.dados_validados import TARGETS, load_dataset, safe_output
from mindscreen.modelo_calibrado import METODOS, Calibrador, ModeloCalibrado

MODELOS = ("dummy", "logistic", "random_forest", "xgboost")


def cross_fitted(scores, y, splits, metodo):
    """Calibra cada fold com um calibrador ajustado apenas nos demais folds."""
    scores, y = np.asarray(scores, dtype=float), np.asarray(y).astype(int)
    out = np.full(len(y), np.nan)
    for train_idx, test_idx in splits:
        out[test_idx] = Calibrador(metodo).fit(scores[train_idx], y[train_idx]).transform(scores[test_idx])
    if np.isnan(out).any():
        raise ValueError("Os folds não cobrem todos os registros")
    return out


def calibrate_scores(oof, y, splits, metodos=METODOS, criterio="brier", bins=10):
    """Escolhe o método pelo critério nas pontuações calibradas fora do fold e o limiar nelas."""
    if criterio != "brier":
        raise ValueError("Critério de calibração suportado: brier")
    y = np.asarray(y).astype(int)
    avaliados = {}
    for metodo in metodos:
        calibrated = cross_fitted(oof, y, splits, metodo)
        avaliados[metodo] = (calibrated, calibration_metrics(y, calibrated, bins=bins)[0])
    escolhido = min(metodos, key=lambda m: avaliados[m][1]["brier"])
    calibrated = avaliados[escolhido][0]
    threshold, f1 = choose_threshold(y, calibrated)
    return {"metodo": escolhido, "calibrador": Calibrador(escolhido).fit(oof, y), "limiar": threshold, "f1_oof": f1,
            "metricas_cv": {m: v[1] for m, v in avaliados.items()}}


def calibrate_experiment(manifest, frame, models_in, models_out, experiment, cal_config):
    import joblib
    from sklearn.base import clone
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    registry_path = models_in / "registro.json"
    log = json.loads((models_in / experiment / "treinamento.json").read_text(encoding="utf-8"))
    config = log["configuracao"]
    dev = frame.loc[frame["ano"].isin(config["anos_desenvolvimento"])]
    features = log["preditores"]
    (models_out / experiment).mkdir(parents=True, exist_ok=True)
    rows = []
    for target in TARGETS:
        subset = dev.loc[dev[target].notna()]
        X, y = subset[features], subset[target].astype(int)
        if len(y) != log["resultados"][target]["registros"]:
            raise ValueError("A população de desenvolvimento difere da usada no treinamento")
        cv = StratifiedKFold(n_splits=config["folds"], shuffle=True, random_state=config["semente"])
        splits = list(cv.split(X, y))
        for name in MODELOS:
            key = f"{experiment}/{target}_{name}"
            base = load_model(registry_path, key, manifest["sha256"])
            entry = log["resultados"][target]["modelos"][name]
            print(f"{key}: calibração", flush=True)
            if name == "dummy":
                # Proporção da classe: já é a probabilidade marginal; nada a calibrar.
                result = {"metodo": "nenhum", "calibrador": Calibrador("nenhum"), "limiar": 0.5, "f1_oof": None, "metricas_cv": {}}
                limiar_bruto = 0.5
            else:
                oof = cross_val_predict(clone(base), X, y, cv=splits, method="predict_proba", n_jobs=config["n_jobs"])
                oof = oof[:, list(base.classes_).index(1)]
                limiar_bruto, _ = choose_threshold(y, oof)
                if not np.isclose(limiar_bruto, entry.get("limiar", limiar_bruto), atol=1e-6):
                    raise ValueError(f"{key}: previsões fora do fold não reproduzem o treinamento")
                result = calibrate_scores(oof, y, splits, cal_config["metodos"], cal_config["criterio"], cal_config["bins_curva"])
            joblib.dump(ModeloCalibrado(base, result["calibrador"]), models_out / experiment / f"{target}_{name}.joblib")
            entry.update({"limiar_sem_calibracao": float(entry.get("limiar", 0.5)), "limiar": float(result["limiar"]), "f1_oof": result["f1_oof"],
                          "calibracao": {"metodo": result["metodo"], "metricas_cv": result["metricas_cv"]}})
            for metodo, metrics in result["metricas_cv"].items():
                rows.append({"experimento": experiment, "target": target, "modelo": name, "metodo": metodo,
                             "escolhido": metodo == result["metodo"], **metrics})
            print(f"  método: {result['metodo']}; limiar calibrado: {result['limiar']:.4f}", flush=True)
    log["calibracao"] = {"data_utc": datetime.now(timezone.utc).isoformat(), "modelos_origem": str(models_in),
                         "configuracao": cal_config,
                         "protocolo": "Pós-hoc sobre os pipelines congelados: previsões fora do fold nos mesmos folds do treinamento (2020–2023); "
                                      "cada método é avaliado por calibração cruzada (calibrador do fold k ajustado nos demais folds); "
                                      "escolhe-se o menor Brier; o limiar maximiza o F1 nas pontuações calibradas fora do fold; "
                                      "o calibrador final é ajustado em todas as previsões fora do fold. 2024 não é usado."}
    (models_out / experiment / "treinamento.json").write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    return rows


def compare_2024(manifest, frame, models_in, models_out, bins):
    """Descrição da calibração em 2024 antes e depois; nenhuma escolha é feita aqui."""
    rows, curves = [], {}
    for experiment in ("A", "B"):
        for target in TARGETS:
            test = frame.loc[frame.ano.eq(2024) & frame[target].notna()]
            for name in MODELOS:
                key = f"{experiment}/{target}_{name}"
                for versao, folder in (("sem_calibracao", models_in), ("calibrado", models_out)):
                    model = load_model(folder / "registro.json", key, manifest["sha256"])
                    features = read_registry(folder / "registro.json")["artefatos"][key]["preditores"]
                    metrics, curve = calibration_metrics(test[target], positive_probability(model, test[features]), bins=bins)
                    rows.append({"experimento": experiment, "target": target, "modelo": name, "versao": versao, **metrics})
                    curves[f"{key}/{versao}"] = curve
    return pd.DataFrame(rows), curves


def run(manifest_path, config_path, models_in, models_out, output, train_config=Path("configs/treinamento.json")):
    from mindscreen.experimentos import register_models, run as evaluate

    manifest, frame = load_dataset(manifest_path)
    cal_config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if not set(cal_config["metodos"]) <= set(METODOS) or not cal_config["metodos"]:
        raise ValueError("Métodos de calibração inválidos")
    models_in, models_out, output = safe_output(models_in), safe_output(models_out), safe_output(output)
    if MODELS_ROOT.resolve() not in models_out.parents or models_out == models_in:
        raise ValueError("Os modelos calibrados devem ficar numa pasta nova dentro de models/")
    if (models_out / "registro.json").exists() or any((models_out / e / "treinamento.json").exists() for e in ("A", "B")):
        raise FileExistsError("Já existem modelos calibrados no destino; escolha outra pasta para preservar os anteriores")
    if read_registry(models_in / "registro.json")["dataset_sha256"] != manifest["sha256"]:
        raise ValueError("Modelos de origem e dataset pertencem a execuções diferentes")
    rows = []
    for experiment in ("A", "B"):
        rows += calibrate_experiment(manifest, frame, models_in, models_out, experiment, cal_config)
    register_models(manifest, models_out)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output / "calibracao_cv.csv", index=False, encoding="utf-8-sig")
    evaluation = evaluate(manifest_path, train_config, models_out, output, do_train=False, bootstrap=cal_config["bootstrap"])
    comparison, curves = compare_2024(manifest, frame, models_in, models_out, cal_config["bins_curva"])
    comparison.to_csv(output / "calibracao_2024.csv", index=False, encoding="utf-8-sig")
    (output / "calibracao_curvas.json").write_text(json.dumps({"curvas": curves, "bins": cal_config["bins_curva"],
                                                                "estrategia": "quantis da pontuação"}, ensure_ascii=False), encoding="utf-8")
    return evaluation, comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, default=Path("data/processed/manifesto.json"))
    parser.add_argument("--config", type=Path, default=Path("configs/calibracao.json"))
    parser.add_argument("--config-treinamento", type=Path, default=Path("configs/treinamento.json"))
    parser.add_argument("--models", type=Path, default=Path("models/experimentos"))
    parser.add_argument("--output-models", type=Path, default=Path("models/experimentos_calibrados"))
    parser.add_argument("--output", type=Path, default=Path("reports/modelagem/v3_calibrada/calibracao"))
    args = parser.parse_args()
    try:
        run(args.manifesto, args.config, args.models, args.output_models, args.output, args.config_treinamento)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        parser.exit(1, f"Calibração não executada: {exc}\n")
    print(f"Modelos calibrados em {args.output_models}; avaliação em {args.output}")


if __name__ == "__main__":
    main()
