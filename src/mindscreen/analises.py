"""Rotina completa de experimentos, associação, SHAP e relatórios."""

import argparse
from pathlib import Path

from mindscreen.associacao import run as association
from mindscreen.experimentos import run as experiments
from mindscreen.explicabilidade import run as explain
from mindscreen.resultados import render_results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, default=Path("data/processed/manifesto.json"))
    parser.add_argument("--config", type=Path, default=Path("configs/treinamento.json"))
    parser.add_argument("--models", type=Path, default=Path("models/experimentos"))
    parser.add_argument("--treinar", action="store_true", help="Treina apenas experimentos ainda não concluídos")
    args = parser.parse_args()
    evaluation = experiments(args.manifesto, args.config, args.models, Path("reports/avaliacao"), args.treinar)
    print("Avaliação temporal concluída", flush=True)
    association_results = association(args.manifesto, Path("reports/associacao"))
    print("Associação ajustada concluída", flush=True)
    explanations = explain(args.manifesto, args.models / "registro.json", Path("reports/figures"))
    print("SHAP concluído", flush=True)
    render_results(evaluation, explanations, association_results, Path("reports/figures"), Path("reports/resultados"))
    print("Relatório: reports/resultados/interpretacao.md", flush=True)


if __name__ == "__main__":
    main()
