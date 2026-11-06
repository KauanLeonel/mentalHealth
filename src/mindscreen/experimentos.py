"""Experimentos A/B com protocolo fixo e avaliação independente de 2024."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from mindscreen.artefatos import MODELS_ROOT, load_model, preprocessing_signature
from mindscreen.avaliacao import binary_metrics, positive_probability
from mindscreen.dados_validados import TARGETS, load_dataset, safe_output
from mindscreen.harmonizacao import sha256
from mindscreen.treinamento import train


def register_models(manifest, models):
    models = Path(models)
    root = MODELS_ROOT.resolve()
    if root not in models.resolve().parents:
        raise ValueError("Os experimentos devem ficar em models/")
    registry = {"origem": "mindscreen-treinamento-local-v1", "dataset_sha256": manifest["sha256"],
                "artefatos": {}, "selecionados": {}, "treinamento": {}, "calibrado": False,
                "classe_positiva": 1, "preprocessamento_sha256": preprocessing_signature(), "criterio_selecao": "ROC AUC média CV 2020–2023", "criado_utc": datetime.now(timezone.utc).isoformat()}
    for experiment in ["A", "B"]:
        log = json.loads((models / experiment / "treinamento.json").read_text(encoding="utf-8"))
        if log["sha256_dataset"] != manifest["sha256"]:
            raise ValueError("Experimentos não usam o mesmo dataset")
        registry["treinamento"][experiment] = log
        for target in TARGETS:
            selected = log["resultados"][target]["selecionado_por_cv"]
            registry["selecionados"][experiment + "/" + target] = experiment + "/" + target + "_" + selected
            for name in log["resultados"][target]["modelos"]:
                filename = target + "_" + name + ".joblib"
                artifact = models / experiment / filename
                registry["artefatos"][experiment + "/" + target + "_" + name] = {
                    "arquivo": experiment + "/" + filename, "sha256": sha256(artifact), "target": target, "algoritmo": name,
                    "preditores": log["preditores"], "roc_auc_cv": log["resultados"][target]["modelos"][name]["roc_auc_cv"]}
    if registry["treinamento"]["A"]["configuracao"] != registry["treinamento"]["B"]["configuracao"]:
        raise ValueError("A e B devem usar a mesma configuração de busca")
    expected = set(registry["treinamento"]["A"]["preditores"]) - {"SCREENTIME"}
    if set(registry["treinamento"]["B"]["preditores"]) != expected:
        raise ValueError("A única diferença de preditores deve ser SCREENTIME")
    for target in TARGETS:
        for field in ["registros", "classes"]:
            if registry["treinamento"]["A"]["resultados"][target][field] != registry["treinamento"]["B"]["resultados"][target][field]:
                raise ValueError("A e B não possuem a mesma população de desenvolvimento")
    (models / "registro.json").write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    return registry


def run(manifest_path, config, models, output, do_train=False):
    manifest, frame = load_dataset(manifest_path)
    models, output = safe_output(models), safe_output(output)
    if do_train:
        expected_config = json.loads(Path(config).read_text(encoding="utf-8"))
        for experiment in ["A", "B"]:
            log_path = models / experiment / "treinamento.json"
            if log_path.exists():
                log = json.loads(log_path.read_text(encoding="utf-8"))
                if log["sha256_dataset"] != manifest["sha256"] or log["configuracao"] != expected_config:
                    raise ValueError("Execução anterior incompatível; escolha outra pasta de modelos")
            else:
                train(manifest_path, config, models / experiment, without_screen=experiment == "B")
    registry = register_models(manifest, models)
    rows, curves = [], {}
    for experiment in ["A", "B"]:
        for target in TARGETS:
            test = frame.loc[frame.ano.eq(2024) & frame[target].notna()]
            if test.empty:
                raise ValueError("Teste temporal de 2024 indisponível")
            for name in ("dummy", "logistic", "random_forest", "xgboost"):
                key = experiment + "/" + target + "_" + name
                model = load_model(models / "registro.json", key, manifest["sha256"])
                features = registry["artefatos"][key]["preditores"]
                scores = positive_probability(model, test[features])
                metrics, curve = binary_metrics(test[target], scores)
                rows.append({"experimento": experiment, "target": target, "modelo": name,
                             "selecionado_cv": key == registry["selecionados"][experiment + "/" + target],
                             "roc_auc_cv": registry["artefatos"][key]["roc_auc_cv"], **metrics})
                curves[key] = curve
    metrics = pd.DataFrame(rows)
    a, b = metrics.loc[metrics.experimento.eq("A")].set_index(["target", "modelo"]), metrics.loc[metrics.experimento.eq("B")].set_index(["target", "modelo"])
    deltas = (a[["roc_auc", "pr_auc", "average_precision", "f1"]] - b[["roc_auc", "pr_auc", "average_precision", "f1"]]).add_prefix("delta_A_menos_B_").reset_index()
    output.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(output / "metricas_2024.csv", index=False, encoding="utf-8-sig")
    deltas.to_csv(output / "ablation.csv", index=False, encoding="utf-8-sig")
    payload = {"dataset_sha256": manifest["sha256"], "metricas": rows, "curvas": curves, "ablation": deltas.to_dict("records"),
               "protocolo": "Cinco folds estratificados idênticos por target em 2020–2023; limiar fixo 0.5; seleção por ROC AUC CV. Teste: todos os elegíveis de 2024, com exclusão apenas do target indeterminado. Métricas amostrais não ponderadas.",
               "pr_auc_definicao": "PR-AUC operacionalizada por Average Precision (AP), sem interpolação linear; área trapezoidal também registrada separadamente.",
               "selecao": registry["selecionados"], "calibrado": False}
    (output / "avaliacao.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, default=Path("data/processed/manifesto.json"))
    parser.add_argument("--config", type=Path, default=Path("configs/treinamento.json"))
    parser.add_argument("--models", type=Path, default=Path("models/experimentos"))
    parser.add_argument("--output", type=Path, default=Path("reports/avaliacao"))
    parser.add_argument("--treinar", action="store_true")
    args = parser.parse_args()
    run(args.manifesto, args.config, args.models, args.output, args.treinar)


if __name__ == "__main__":
    main()
