"""Rotina completa de experimentos, associação, SHAP e relatórios."""

import argparse
import json
from pathlib import Path

import pandas as pd

from mindscreen.artefatos import read_registry
from mindscreen.associacao import run as association
from mindscreen.dados_validados import safe_output
from mindscreen.experimentos import run as experiments
from mindscreen.explicabilidade import run as explain
from mindscreen.resultados import render_results

REPORTS_ROOT = Path("reports")
REPORTS_V2 = REPORTS_ROOT / "modelagem/v2_limiar_cv"


def load_calibration(folder):
    """Lê as saídas de mindscreen.calibracao para o relatório; nada é recalculado aqui."""
    folder = Path(folder)
    curves = json.loads((folder / "calibracao_curvas.json").read_text(encoding="utf-8"))
    return {"cv": pd.read_csv(folder / "calibracao_cv.csv", encoding="utf-8-sig").to_dict("records"),
            "teste": pd.read_csv(folder / "calibracao_2024.csv", encoding="utf-8-sig").to_dict("records"),
            "curvas": curves["curvas"], "bins": curves["bins"]}


def run(manifest, config, models, reports, do_train=False, calibration=None):
    reports = safe_output(reports)
    if calibration is not None and Path(reports).resolve() in (REPORTS_ROOT.resolve(), REPORTS_V2.resolve()):
        raise ValueError("Relatórios de modelos calibrados devem ir para uma pasta própria (ex.: reports/modelagem/v3_calibrada)")
    registry = Path(models) / "registro.json"
    if registry.exists() and read_registry(registry)["calibrado"] and calibration is None:
        raise ValueError("Modelos calibrados exigem --calibracao com as saídas de mindscreen.calibracao")
    evaluation = experiments(manifest, config, models, reports / "avaliacao", do_train)
    print("Avaliação temporal concluída", flush=True)
    association_results = association(manifest, reports / "associacao")
    print("Associação ajustada concluída", flush=True)
    explanations = explain(manifest, Path(models) / "registro.json", reports / "figuras")
    print("SHAP concluído", flush=True)
    render_results(evaluation, explanations, association_results, reports / "figuras", reports / "resultados",
                   load_calibration(calibration) if calibration is not None else None)
    print(f"Relatório: {reports / 'resultados/interpretacao.md'}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, default=Path("data/processed/manifesto.json"))
    parser.add_argument("--config", type=Path, default=Path("configs/treinamento.json"))
    parser.add_argument("--models", type=Path, default=Path("models/experimentos"))
    parser.add_argument("--reports", type=Path, default=REPORTS_V2, help="Pasta da versão em reports/modelagem (avaliacao, associacao, figuras, resultados)")
    parser.add_argument("--calibracao", type=Path, default=None, help="Saídas de mindscreen.calibracao, para modelos calibrados")
    parser.add_argument("--treinar", action="store_true", help="Treina apenas experimentos ainda não concluídos")
    args = parser.parse_args()
    try:
        run(args.manifesto, args.config, args.models, args.reports, args.treinar, args.calibracao)
    except (FileNotFoundError, ValueError) as exc:
        parser.exit(1, f"Análises não executadas: {exc}\n")


if __name__ == "__main__":
    main()
