"""Análise dos resultados da contribuição incremental (v4): figuras, tabelas de robustez e relatório.

Somente lê as saídas de `mindscreen.contribuicao`; nenhum modelo é ajustado e nenhum valor é digitado à mão.
Grava em <pasta da versão>/analise/ e recusa sobrescrever uma análise existente.
"""

import argparse
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from mindscreen.dados_validados import TARGETS, safe_output
from mindscreen.painel import ROTINA_ROTULOS, contribution_chart, routine_profile_chart

PASTA = "analise"
ROTULOS_TARGET = {"depressao_atual": "Depressão atual", "ansiedade_atual": "Ansiedade atual"}
ROTULOS_MODELO = {"logistic": "Regressão logística", "xgboost": "XGBoost", "random_forest": "Floresta aleatória"}


def carregar(folder, manifest_path):
    folder = Path(folder)
    payload = json.loads((folder / "contribuicao.json").read_text(encoding="utf-8"))
    sha = json.loads(Path(manifest_path).read_text(encoding="utf-8"))["sha256"]
    if payload.get("dataset_sha256") != sha:
        raise ValueError("Resultados não correspondem ao dataset atual do manifesto")
    contrib = pd.read_csv(folder / "contribuicoes.csv", encoding="utf-8-sig")
    metrics = pd.read_csv(folder / "metricas.csv", encoding="utf-8-sig", dtype={"ano_avaliado": str})
    perfil = pd.read_csv(folder / "perfil_rotina.csv", encoding="utf-8-sig", dtype={"periodo": str})
    return payload, contrib, metrics, perfil


def consistencia_por_ano(contrib, anos):
    """Formato longo: ΔAUC incremental de cada fator em cada edição deixada de fora."""
    inc = contrib.loc[contrib.tipo.eq("incremental"), ["target", "modelo", "fator", *[f"delta_auc_{a}" for a in anos]]]
    long = inc.melt(id_vars=["target", "modelo", "fator"], value_vars=[f"delta_auc_{a}" for a in anos], var_name="ano", value_name="delta_auc")
    long["ano"] = long.ano.str.removeprefix("delta_auc_").astype(int)
    return long.sort_values(["target", "modelo", "fator", "ano"]).reset_index(drop=True)


def sobreposicao(contrib):
    """Quanto da contribuição isolada de cada fator permanece quando os demais fatores já estão no modelo."""
    keys = ["target", "modelo", "fator"]
    iso = contrib.loc[contrib.tipo.eq("isolado"), keys + ["delta_auc"]].rename(columns={"delta_auc": "delta_isolado"})
    inc = contrib.loc[contrib.tipo.eq("incremental"), keys + ["delta_auc", "delta_auc_ic_inf", "delta_auc_ic_sup"]].rename(columns={"delta_auc": "delta_incremental"})
    table = iso.merge(inc, on=keys, validate="one_to_one")
    table["fracao_que_permanece"] = table.delta_incremental / table.delta_isolado
    return table


def concordancia_modelos(contrib, modelos):
    """ΔAUC incremental lado a lado entre modelos, com ordem dos fatores em cada um."""
    inc = contrib.loc[contrib.tipo.eq("incremental")].copy()
    inc["posicao"] = inc.groupby(["target", "modelo"]).delta_auc.rank(ascending=False, method="min").astype(int)
    wide = inc.pivot_table(index=["target", "fator"], columns="modelo", values=["delta_auc", "posicao", "delta_auc_ponderada"])
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    return wide.reset_index()


def faixas(contrib, nomes):
    rows = []
    for r in contrib.loc[contrib.tipo.eq("incremental")].to_dict("records"):
        for nome in nomes:
            rows.append({"target": r["target"], "modelo": r["modelo"], "fator": r["fator"], "faixa_etaria": nome,
                         "delta_auc": r[f"delta_auc_faixa_{nome}"], "ic_inf": r[f"delta_auc_faixa_{nome}_ic_inf"], "ic_sup": r[f"delta_auc_faixa_{nome}_ic_sup"]})
    return pd.DataFrame(rows)


def grafico_por_ano(long, target, modelo):
    table = long.loc[long.target.eq(target) & long.modelo.eq(modelo)].copy()
    table["Fator"] = table.fator.map(ROTINA_ROTULOS)
    fig = px.line(table, x="ano", y="delta_auc", color="Fator", markers=True, title=f"Contribuição incremental por edição — {ROTULOS_TARGET[target]}",
                  labels={"ano": "Edição prevista (deixada fora do ajuste)", "delta_auc": "Diferença na ROC AUC"})
    fig.add_hline(y=0, line_dash="dot", line_color="#8a8f9c")
    fig.update_layout(template="plotly_white", height=380, xaxis={"dtick": 1})
    return fig


def grafico_faixas(tabela, target, foco="SCREENTIME"):
    table = tabela.loc[tabela.target.eq(target) & tabela.fator.eq(foco)]
    fig = go.Figure()
    for modelo, group in table.groupby("modelo"):
        fig.add_trace(go.Bar(x=group.faixa_etaria, y=group.delta_auc, name=ROTULOS_MODELO.get(modelo, modelo),
                             error_y={"type": "data", "symmetric": False, "array": group.ic_sup - group.delta_auc, "arrayminus": group.delta_auc - group.ic_inf}))
    fig.update_layout(template="plotly_white", barmode="group", height=340, title=f"Contribuição incremental do tempo de tela por faixa etária — {ROTULOS_TARGET[target]}",
                      xaxis_title="Faixa etária (anos)", yaxis_title="Diferença na ROC AUC")
    return fig


def grafico_conjuntos(metrics, target, conjuntos):
    table = metrics.loc[metrics.target.eq(target) & metrics.ano_avaliado.eq("todos")].copy()
    table["conjunto"] = pd.Categorical(table.conjunto, categories=list(conjuntos), ordered=True)
    table = table.sort_values("conjunto")
    table["Modelo"] = table.modelo.map(ROTULOS_MODELO)
    fig = px.bar(table, x="roc_auc", y="conjunto", color="Modelo", barmode="group", orientation="h",
                 title=f"ROC AUC fora do ano por conjunto de preditores — {ROTULOS_TARGET[target]}", labels={"roc_auc": "ROC AUC", "conjunto": ""})
    fig.update_layout(template="plotly_white", height=520, xaxis={"range": [0.5, max(0.9, float(table.roc_auc.max()) + 0.02)]})
    return fig


def grafico_tela_por_ano(perfil, anos):
    table = perfil.loc[perfil.variavel.eq("SCREENTIME") & perfil.categoria.eq(perfil.loc[perfil.variavel.eq("SCREENTIME")].categoria.max())
                       & perfil.periodo.isin([str(a) for a in anos])].copy()
    rotulo = table.rotulo_categoria.iloc[0]
    fig = px.line(table, x="periodo", y="percentual_ponderado", color="faixa_etaria", markers=True,
                  title=f"Tempo de tela “{rotulo}” por edição (% ponderado)", labels={"periodo": "Edição", "percentual_ponderado": "% ponderado", "faixa_etaria": "Idade"})
    fig.update_layout(template="plotly_white", height=340)
    return fig, table


def _num(x, casas=4):
    return "—" if pd.isna(x) else f"{x:.{casas}f}".replace(".", ",")


def _pct(x):
    return f"{x * 100:.0f}%"


def relatorio(payload, contrib, metrics, perfil, sobre, concord, long, faixa, tela_ano, v3=None):
    cfg = payload["configuracao"]
    principal, foco, anos = cfg["modelo_principal"], cfg["fator_foco"], cfg["anos"]
    outros_modelos = [m for m in cfg["modelos"] if m != principal]
    L = ["# Análise da contribuição incremental do tempo de tela (v4)", "",
         "Relatório gerado por `python -m mindscreen.analise_contribuicao` a partir das saídas de `mindscreen.contribuicao`. "
         "Nenhum modelo foi ajustado nesta etapa e todos os números foram lidos dos arquivos da versão.", "",
         f"**Pergunta.** {payload['resumo']['pergunta']}", "", f"**Protocolo.** {payload['protocolo']}", "", "## População analisada", "",
         "| Desfecho | Registros | Positivos | Excluídos (desfecho indeterminado) | " + " | ".join(str(a) for a in anos) + " |",
         "|---|---|---|---|" + "---|" * len(anos)]
    for t in TARGETS:
        p = payload["populacao"][t]
        L.append(f"| {ROTULOS_TARGET[t]} | {p['registros']} | {p['positivos']} ({_pct(p['positivos'] / p['registros'])}) | {p['excluidos_target_ausente']} | "
                 + " | ".join(str(p["por_ano"][str(a)]) for a in anos) + " |")
    L += ["", "## 1. Resposta principal", ""]
    for bloco in payload["resumo"]["blocos"]:
        L += [f"**{bloco['rotulo'].capitalize()}** ({ROTULOS_MODELO[principal].lower()})", "", *[f"- {f}" for f in bloco["frases"]], ""]
    L += ["Figuras: `figuras/<desfecho>_incremental.html`, `figuras/<desfecho>_auc_conjuntos.html`.", "",
          "## 2. Sobreposição com os outros fatores de rotina", "",
          "Contribuição de cada fator sozinho (acrescentado a idade e sexo) e depois de os demais fatores entrarem no modelo. "
          "A fração que permanece indica quanto da informação do fator não está contida nos outros. A correlação entre fatores não indica qual deles vem primeiro.", "",
          "| Desfecho | Modelo | Fator | Δ isolado | Δ incremental | Fração que permanece |", "|---|---|---|---|---|---|"]
    for r in sobre.sort_values(["target", "modelo", "delta_incremental"], ascending=[True, True, False]).itertuples():
        L.append(f"| {ROTULOS_TARGET[r.target]} | {r.modelo} | {ROTINA_ROTULOS[r.fator]} | {_num(r.delta_isolado)} | {_num(r.delta_incremental)} | {_pct(r.fracao_que_permanece)} |")
    for t in TARGETS:
        s = sobre.loc[sobre.target.eq(t) & sobre.modelo.eq(principal) & sobre.fator.eq(foco)].iloc[0]
        L.append("")
        L.append(f"- {ROTULOS_TARGET[t]}: sozinho, o tempo de tela acrescenta {_num(s.delta_isolado)} à ROC AUC de idade e sexo. "
                 f"Com os demais fatores já no modelo, acrescenta {_num(s.delta_incremental)}, ou seja, {_pct(s.fracao_que_permanece)} da contribuição isolada.")
    L += ["", "Figura: `figuras/<desfecho>_isolado.html`.", "", "## 3. Consistência entre edições", "",
          f"ΔAUC incremental do {ROTINA_ROTULOS[foco].lower()} em cada edição prevista por modelos ajustados nas demais:", "",
          "| Desfecho | Modelo | " + " | ".join(str(a) for a in anos) + " | Mínimo | Máximo | Edições > 0 |", "|---|---|" + "---|" * (len(anos) + 3)]
    for (t, m), g in long.loc[long.fator.eq(foco)].groupby(["target", "modelo"]):
        L.append(f"| {ROTULOS_TARGET[t]} | {m} | " + " | ".join(_num(v) for v in g.delta_auc) + f" | {_num(g.delta_auc.min())} | {_num(g.delta_auc.max())} | {int((g.delta_auc > 0).sum())} de {len(g)} |")
    L += ["", "A redação do item de tempo de tela mudou em 2024 (exclusão explícita de tarefas escolares). A tabela permite observar essa edição separadamente, mas não corrige a mudança.", "",
          "Figura: `figuras/<desfecho>_por_ano.html`.", "", "## 4. Robustez: modelos e pesos amostrais", "",
          "| Desfecho | Fator | " + " | ".join(f"Δ {m} | posição {m}" for m in cfg["modelos"]) + f" | Δ ponderado ({principal}) |",
          "|---|---|" + "---|---|" * len(cfg["modelos"]) + "---|"]
    for r in concord.to_dict("records"):
        L.append(f"| {ROTULOS_TARGET[r['target']]} | {ROTINA_ROTULOS[r['fator']]} | " + " | ".join(f"{_num(r[f'delta_auc_{m}'])} | {int(r[f'posicao_{m}'])}º" for m in cfg["modelos"])
                 + f" | {_num(r[f'delta_auc_ponderada_{principal}'])} |")
    for t in TARGETS:
        sub = concord.loc[concord.target.eq(t)]
        mesma = all((sub[f"posicao_{principal}"] == sub[f"posicao_{m}"]).all() for m in outros_modelos)
        L.append("")
        L.append(f"- {ROTULOS_TARGET[t]}: a ordem dos fatores " + ("é a mesma" if mesma else "não é a mesma") + " entre os modelos.")
    L += ["", "A AUC ponderada usa o peso FWC como análise de sensibilidade e não incorpora a variância do desenho amostral.", "",
          "## 5. Faixas etárias", "", "| Desfecho | Modelo | Faixa | ΔAUC do tempo de tela | IC 95% |", "|---|---|---|---|---|"]
    for r in faixa.loc[faixa.fator.eq(foco)].itertuples():
        L.append(f"| {ROTULOS_TARGET[r.target]} | {r.modelo} | {r.faixa_etaria} | {_num(r.delta_auc)} | {_num(r.ic_inf)} a {_num(r.ic_sup)} |")
    L += ["", "Dentro de cada faixa, a idade varia menos, e por isso as AUCs de cada faixa não são comparáveis com a AUC total. Compare as faixas entre si.", "",
          "Figura: `figuras/<desfecho>_faixas.html`.", "", "## 6. Perfil da rotina na NSCH (percentuais ponderados)", "",
          "Estimativas pontuais com os pesos da pesquisa, para crianças e adolescentes de 6 a 17 anos nos EUA, sem intervalos. Não servem como referência para uma família específica.", ""]
    pooled = perfil.loc[perfil.periodo.eq("2020–2024")]
    nomes_faixa = list(cfg["faixas_etarias"])
    for var in cfg["fatores_rotina"]:
        sub = pooled.loc[pooled.variavel.eq(var)]
        L += [f"**{ROTINA_ROTULOS[var]}**", "", "| Categoria | " + " | ".join(nomes_faixa) + " |", "|---|" + "---|" * len(nomes_faixa)]
        for cat, g in sub.groupby("categoria"):
            valores = {r.faixa_etaria: r.percentual_ponderado for r in g.itertuples()}
            L.append(f"| {g.rotulo_categoria.iloc[0]} | " + " | ".join(f"{valores.get(f, float('nan')):.1f}%".replace(".", ",") for f in nomes_faixa) + " |")
        L.append("")
    L += [f"Tempo de tela na categoria mais alta (“{tela_ano.rotulo_categoria.iloc[0]}”), por edição:", "", "| Faixa | " + " | ".join(str(a) for a in anos) + " |", "|---|" + "---|" * len(anos)]
    for f, g in tela_ano.groupby("faixa_etaria", sort=False):
        L.append(f"| {f} | " + " | ".join(f"{v:.1f}%".replace(".", ",") for v in g.sort_values("periodo").percentual_ponderado) + " |")
    L += ["", "Figuras: `figuras/perfil_<variável>.html`, `figuras/tela_por_ano.html`.", ""]
    if v3 is not None:
        L += ["## 7. Comparação com a versão anterior (v3)", "",
              "A v3 avaliou modelos com e sem tempo de tela em 2024, com hiperparâmetros buscados em 2020–2023. A v4 usa validação deixando um ano fora em todas as edições. "
              "Os protocolos são diferentes; a comparação serve apenas para verificar se a ordem de grandeza se mantém.", "",
              "| Desfecho | Modelo | ΔAUC v3 (teste 2024) | ΔAUC v4 (todas as edições) | ΔAUC v4 (só 2024) |", "|---|---|---|---|---|"]
        for r in v3.itertuples():
            L.append(f"| {ROTULOS_TARGET[r.target]} | {r.modelo} | {_num(r.delta_v3)} | {_num(r.delta_v4)} | {_num(r.delta_v4_2024)} |")
        L.append("")
    L += ["## Limites", "", *[f"- {l}" for l in payload["limites"]], ""]
    return "\n".join(L)


def comparar_v3(v3_ablation, contrib, foco):
    path = Path(v3_ablation)
    if not path.exists():
        return None
    old = pd.read_csv(path, encoding="utf-8-sig")
    contrib = contrib if "delta_auc_2024" in contrib else contrib.assign(delta_auc_2024=float("nan"))
    inc = contrib.loc[contrib.tipo.eq("incremental") & contrib.fator.eq(foco), ["target", "modelo", "delta_auc", "delta_auc_2024"]]
    table = old[["target", "modelo", "delta_A_menos_B_roc_auc"]].merge(inc, on=["target", "modelo"])
    return table.rename(columns={"delta_A_menos_B_roc_auc": "delta_v3", "delta_auc": "delta_v4", "delta_auc_2024": "delta_v4_2024"})


def run(folder, manifest_path, v3_ablation=None):
    folder = safe_output(folder)
    out = folder / PASTA
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"{out} já contém uma análise; ela foi preservada")
    payload, contrib, metrics, perfil = carregar(folder, manifest_path)
    cfg = payload["configuracao"]
    principal, foco, anos = cfg["modelo_principal"], cfg["fator_foco"], cfg["anos"]
    long = consistencia_por_ano(contrib, anos)
    sobre = sobreposicao(contrib)
    concord = concordancia_modelos(contrib, cfg["modelos"])
    faixa = faixas(contrib, list(cfg["faixas_etarias"]))
    tela_fig, tela_ano = grafico_tela_por_ano(perfil, anos)
    v3 = comparar_v3(v3_ablation, contrib, foco) if v3_ablation else None
    figuras = {"tela_por_ano": tela_fig}
    for t in TARGETS:
        figuras[f"{t}_incremental"] = contribution_chart(contrib, t, principal, "incremental", foco)
        figuras[f"{t}_isolado"] = contribution_chart(contrib, t, principal, "isolado", foco)
        figuras[f"{t}_por_ano"] = grafico_por_ano(long, t, principal)
        figuras[f"{t}_faixas"] = grafico_faixas(faixa, t, foco)
        figuras[f"{t}_auc_conjuntos"] = grafico_conjuntos(metrics, t, payload["conjuntos"])
    for var in cfg["fatores_rotina"]:
        figuras[f"perfil_{var}"] = routine_profile_chart(perfil, var)
    (out / "figuras").mkdir(parents=True, exist_ok=True)
    for name, fig in figuras.items():
        fig.write_html(out / "figuras" / f"{name}.html", include_plotlyjs="directory")
        (out / "figuras" / f"{name}.json").write_text(fig.to_json(), encoding="utf-8")
    long.to_csv(out / "consistencia_por_ano.csv", index=False, encoding="utf-8-sig")
    sobre.to_csv(out / "sobreposicao.csv", index=False, encoding="utf-8-sig")
    concord.to_csv(out / "concordancia_modelos.csv", index=False, encoding="utf-8-sig")
    faixa.to_csv(out / "faixas_etarias.csv", index=False, encoding="utf-8-sig")
    if v3 is not None:
        v3.to_csv(out / "comparacao_v3.csv", index=False, encoding="utf-8-sig")
    texto = relatorio(payload, contrib, metrics, perfil, sobre, concord, long, faixa, tela_ano, v3)
    (out / "relatorio.md").write_text(texto, encoding="utf-8")
    (out / "analise.json").write_text(json.dumps({"dataset_sha256": payload["dataset_sha256"], "origem": str(folder.name),
                                                  "figuras": sorted(figuras), "comparacao_v3": v3 is not None}, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--resultados", type=Path, default=Path("reports/modelagem/v4_contribuicao"))
    parser.add_argument("--manifesto", type=Path, default=Path("data/processed/manifesto.json"))
    parser.add_argument("--v3", type=Path, default=Path("reports/modelagem/v3_calibrada/avaliacao/ablation.csv"),
                        help="ablation.csv da v3 para comparação (ignorado se ausente)")
    args = parser.parse_args(argv)
    try:
        out = run(args.resultados, args.manifesto, args.v3)
    except (FileNotFoundError, FileExistsError, ValueError, KeyError) as exc:
        parser.exit(1, f"Análise não executada: {exc}\n")
    print(f"Relatório: {out / 'relatorio.md'}")


if __name__ == "__main__":
    main()
