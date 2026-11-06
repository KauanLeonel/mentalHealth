"""Figuras e interpretação derivadas exclusivamente de resultados calculados."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from mindscreen.dados_validados import TARGETS
from mindscreen.explicabilidade import save_figure


def render_results(evaluation, explanations, association, figures, output):
    figures, output = Path(figures), Path(output)
    figures.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    metrics = pd.DataFrame(evaluation["metricas"])
    for experiment in ["A", "B"]:
        for target in TARGETS:
            rows = metrics.loc[metrics.experimento.eq(experiment) & metrics.target.eq(target)]
            for curve_name, title, xlabel, ylabel in [("roc", "ROC", "Taxa de falsos positivos", "Sensibilidade"), ("pr", "Precisão–Recall", "Recall", "Precisão")]:
                figure = go.Figure()
                for _, row in rows.iterrows():
                    key = experiment + "/" + target + "_" + row["modelo"]
                    curve = evaluation["curvas"][key][curve_name]
                    figure.add_trace(go.Scatter(x=curve["x"], y=curve["y"], mode="lines", name=row["modelo"]))
                figure.update_layout(title=f"{title} temporal — {target} — {experiment}", xaxis_title=xlabel, yaxis_title=ylabel)
                save_figure(figure, figures / f"{experiment}_{target}_{curve_name}")
            for _, row in rows.iterrows():
                matrix = [[int(row.tn), int(row.fp)], [int(row.fn), int(row.tp)]]
                fig = px.imshow(matrix, x=["Predito 0", "Predito 1"], y=["Observado 0", "Observado 1"], text_auto=True, color_continuous_scale="Purples", title=f"Matriz de confusão — {target} — {row['modelo']} — {experiment}")
                save_figure(fig, figures / f"{experiment}_{target}_{row['modelo']}_confusao")
    ablation = pd.DataFrame(evaluation["ablation"])
    for target in TARGETS:
        part = ablation.loc[ablation.target.eq(target)].melt(id_vars=["target", "modelo"], value_vars=["delta_A_menos_B_roc_auc", "delta_A_menos_B_pr_auc", "delta_A_menos_B_f1"], var_name="metrica", value_name="diferenca")
        fig = px.bar(part, x="modelo", y="diferenca", color="metrica", barmode="group", title=f"A com tela − B sem tela — {target}")
        save_figure(fig, figures / f"{target}_ablation")
    ors = pd.DataFrame(association["odds_ratios"])
    fig = px.scatter(ors, x="categoria_screentime", y="odds_ratio_ajustada_amostral", color="target", title="Odds ratios ajustadas amostrais — referência: menos de 1 hora")
    fig.add_hline(y=1, line_dash="dash")
    save_figure(fig, figures / "odds_ratios")
    lines = ["# Modelos, explicabilidade e contribuição preditiva de SCREENTIME", "", evaluation["protocolo"], "", evaluation["pr_auc_definicao"],
             "", "F1 usa limiar predefinido 0,5. As métricas são amostrais, não ponderadas, sem intervalos de confiança. O modelo escolhido é o de maior ROC AUC na validação cruzada de desenvolvimento, mesmo que outro tenha desempenho temporal superior.",
             "", "## Comparação por desfecho"]
    summary = {}
    for target in TARGETS:
        a = metrics.loc[metrics.target.eq(target) & metrics.experimento.eq("A") & metrics.selecionado_cv].iloc[0]
        b = metrics.loc[metrics.target.eq(target) & metrics.experimento.eq("B") & metrics.selecionado_cv].iloc[0]
        fixed = ablation.loc[ablation.target.eq(target) & ablation.modelo.eq(a["modelo"])].iloc[0]
        delta = float(fixed.delta_A_menos_B_roc_auc)
        conclusion = "SCREENTIME não melhorou a ROC AUC temporal nesta comparação." if delta <= 0 else "SCREENTIME apresentou incremento pontual de ROC AUC temporal nesta comparação; sua relevância e incerteza não foram estabelecidas por um teste inferencial."
        if float(fixed.delta_A_menos_B_pr_auc) <= 0:
            conclusion += " PR-AUC/AP não melhorou."
        if float(fixed.delta_A_menos_B_f1) <= 0:
            conclusion += " F1 no limiar fixo não melhorou."
        lines.extend(["", f"### {target}", f"- Selecionado em A por CV: {a['modelo']}. ROC AUC 2024: {a.roc_auc:.6f}; PR-AUC/AP: {a.pr_auc:.6f}; F1: {a.f1:.6f}.",
                      f"- Selecionado em B por CV: {b['modelo']}. ROC AUC 2024: {b.roc_auc:.6f}; PR-AUC/AP: {b.pr_auc:.6f}; F1: {b.f1:.6f}.",
                      f"- Comparando a mesma família {a['modelo']}, A − B: ROC AUC {delta:+.6f}; PR-AUC/AP {fixed.delta_A_menos_B_pr_auc:+.6f}; F1 {fixed.delta_A_menos_B_f1:+.6f}.", f"- {conclusion}"])
        explanation = explanations["targets"].get(target, {})
        factors = []
        if explanation.get("disponivel"):
            factors = [v["variavel"] for v in explanation["importancia"][:3]]
            lines.extend([f"- Maiores atribuições globais médias absolutas de SHAP: {', '.join(factors)}.",
                          f"- SHAP da classe 1, método {explanation['metodo']}, unidade {explanation['unidade']}, {explanation['n_amostra']} observações de 2024 e {explanation['n_background']} referências de desenvolvimento.",
                          f"- Erro máximo da verificação de aditividade: {explanation['max_erro_aditividade']:.8g}."])
            for category in explanation["screentime"]:
                lines.append(f"- Categoria SCREENTIME {category['categoria']}: contribuição SHAP média {category['contribuicao_media']:+.6f} ({category['n']} observações explicadas), relativa ao background e às demais variáveis; não equivale a efeito isolado.")
        else:
            lines.append("- SHAP indisponível para o modelo selecionado; consultar registro de compatibilidade.")
        summary[target] = {"modelo_selecionado_A": a["modelo"], "modelo_selecionado_B": b["modelo"], "delta_mesma_familia_roc_auc": delta,
                           "delta_mesma_familia_pr_auc": float(fixed.delta_A_menos_B_pr_auc), "delta_mesma_familia_f1": float(fixed.delta_A_menos_B_f1),
                           "interpretacao": conclusion, "fatores_shap": factors}
    lines.extend(["", "## Associação ajustada", association["interpretacao"], ""])
    for row in association["odds_ratios"]:
        lines.append(f"- {row['target']}, categoria {row['categoria_screentime']} vs {row['referencia']}: OR {row['odds_ratio_ajustada_amostral']:.4f} (n={row['n_casos_completos']}).")
    lines.extend(["", "## Limitações", "", explanations["limitacoes"],
                  "As magnitudes SHAP em log-odds e em probabilidade não devem ser comparadas diretamente entre modelos.",
                  "A ablation mede desempenho incremental sob duas buscas comparáveis; não mede efeito causal da exposição. Diferenças pequenas ou discordantes entre métricas não demonstram ganho robusto. O teste de 2024 não deve ser reutilizado para ajustar decisões após observar estes resultados.",
                  "Os scores dos classificadores não foram calibrados. O simulador apresenta o rótulo de pesquisa e a pontuação bruta, sem alegar probabilidade clínica validada. Resultados dependem do relato de responsáveis na pesquisa dos Estados Unidos e não são automaticamente transportáveis a indivíduos ou à população brasileira.",
                  "O universo e algumas instruções variaram entre edições; consulte docs/harmonizacao.md. Ausência de dados pode introduzir seleção. Os resultados não estabelecem que o uso de telas provoca depressão ou ansiedade."])
    (output / "interpretacao.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "resumo.json").write_text(json.dumps({"targets": summary, "dataset_sha256": evaluation["dataset_sha256"]}, ensure_ascii=False, indent=2), encoding="utf-8")


