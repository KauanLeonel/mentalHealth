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
             "", "F1, recall e precisão usam o limiar de cada modelo escolhido na validação cruzada de 2020–2023 (máximo F1 fora do fold), sem consultar 2024. As métricas são amostrais e não ponderadas; intervalos de 95% vêm de bootstrap pareado dos registros de 2024 e não incorporam o desenho complexo da pesquisa. O modelo escolhido é o de maior ROC AUC na validação cruzada de desenvolvimento, mesmo que outro tenha desempenho temporal superior.",
             "", "## Comparação por desfecho"]
    summary = {}
    for target in TARGETS:
        a = metrics.loc[metrics.target.eq(target) & metrics.experimento.eq("A") & metrics.selecionado_cv].iloc[0]
        b = metrics.loc[metrics.target.eq(target) & metrics.experimento.eq("B") & metrics.selecionado_cv].iloc[0]
        fixed = ablation.loc[ablation.target.eq(target) & ablation.modelo.eq(a["modelo"])].iloc[0]
        delta = float(fixed.delta_A_menos_B_roc_auc)
        ci = next((r for r in evaluation.get("intervalos", []) if r["target"] == target and r["modelo"] == a["modelo"]), None)
        if ci is None:
            conclusion = "SCREENTIME não melhorou a ROC AUC temporal nesta comparação." if delta <= 0 else "SCREENTIME apresentou incremento pontual de ROC AUC temporal nesta comparação; sua incerteza não foi estimada."
        elif ci["roc_auc_delta_ic_inf"] > 0:
            conclusion = "O IC 95% bootstrap da diferença de ROC AUC A − B fica inteiramente acima de zero: o ganho preditivo de SCREENTIME é pequeno, mas distinguível de zero nesta amostra."
        elif ci["roc_auc_delta_ic_sup"] < 0:
            conclusion = "O IC 95% bootstrap da diferença de ROC AUC A − B fica inteiramente abaixo de zero: SCREENTIME piorou a ROC AUC temporal nesta amostra."
        else:
            conclusion = "O IC 95% bootstrap da diferença de ROC AUC A − B inclui zero: o ganho preditivo de SCREENTIME não é distinguível de zero nesta amostra."
        if float(fixed.delta_A_menos_B_pr_auc) <= 0:
            conclusion += " PR-AUC/AP não melhorou."
        if float(fixed.delta_A_menos_B_f1) <= 0:
            conclusion += " F1 no limiar escolhido por CV não melhorou."
        lines.extend(["", f"### {target}", f"- Selecionado em A por CV: {a['modelo']}. ROC AUC 2024: {a.roc_auc:.6f}; PR-AUC/AP: {a.pr_auc:.6f}; F1: {a.f1:.6f}; limiar {a.threshold:.4f} (recall {a.recall:.4f}, precisão {a.precision:.4f}).",
                      f"- Selecionado em B por CV: {b['modelo']}. ROC AUC 2024: {b.roc_auc:.6f}; PR-AUC/AP: {b.pr_auc:.6f}; F1: {b.f1:.6f}.",
                      f"- Comparando a mesma família {a['modelo']}, A − B: ROC AUC {delta:+.6f}; PR-AUC/AP {fixed.delta_A_menos_B_pr_auc:+.6f}; F1 {fixed.delta_A_menos_B_f1:+.6f}."])
        if ci is not None:
            lines.append(f"- IC 95% bootstrap ({ci['reamostras_validas']} reamostras): ROC AUC A [{ci['roc_auc_A_ic_inf']:.4f}; {ci['roc_auc_A_ic_sup']:.4f}]; A − B ROC AUC [{ci['roc_auc_delta_ic_inf']:+.4f}; {ci['roc_auc_delta_ic_sup']:+.4f}]; A − B AP [{ci['average_precision_delta_ic_inf']:+.4f}; {ci['average_precision_delta_ic_sup']:+.4f}].")
        lines.append(f"- {conclusion}")
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
                           "interpretacao": conclusion, "fatores_shap": factors, "intervalo_bootstrap": ci}
    lines.extend(["", "## Associação ajustada", association["interpretacao"], ""])
    for row in association["odds_ratios"]:
        lines.append(f"- {row['target']}, categoria {row['categoria_screentime']} vs {row['referencia']}: OR {row['odds_ratio_ajustada_amostral']:.4f} (n={row['n_casos_completos']}).")
    lines.extend(["", "## Limitações", "", explanations["limitacoes"],
                  "As magnitudes SHAP em log-odds e em probabilidade não devem ser comparadas diretamente entre modelos.",
                  "A ablation mede desempenho incremental sob duas buscas comparáveis; não mede efeito causal da exposição. Diferenças pequenas ou discordantes entre métricas não demonstram ganho robusto. O teste de 2024 não deve ser reutilizado para ajustar decisões após observar estes resultados.",
                  "Transparência: a revisão do protocolo (scale_pos_weight no XGBoost e limiar por CV) foi motivada pelo baixo recall observado na primeira avaliação de 2024. As escolhas em si usam apenas 2020–2023, mas 2024 deixou de ser um teste completamente cego; a execução anterior está preservada em models/experimentos_v1_limiar05 e reports/_anterior_2026-11-19.",
                  "Os scores dos classificadores não foram calibrados. O simulador apresenta o rótulo de pesquisa e a pontuação bruta, sem alegar probabilidade clínica validada. Resultados dependem do relato de responsáveis na pesquisa dos Estados Unidos e não são automaticamente transportáveis a indivíduos ou à população brasileira.",
                  "O universo e algumas instruções variaram entre edições; consulte docs/harmonizacao.md. Ausência de dados pode introduzir seleção. Os resultados não estabelecem que o uso de telas provoca depressão ou ansiedade."])
    (output / "interpretacao.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "resumo.json").write_text(json.dumps({"targets": summary, "dataset_sha256": evaluation["dataset_sha256"]}, ensure_ascii=False, indent=2), encoding="utf-8")


