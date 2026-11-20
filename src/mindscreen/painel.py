"""Agregações e leitura de resultados compartilhadas pela interface e pelos testes."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio

from mindscreen.dados_validados import TARGETS

LABELS = {"depressao_atual": "Depressão atual", "ansiedade_atual": "Ansiedade atual", "SCREENTIME": "Tempo de tela",
          "SC_AGE_YEARS": "Idade", "SC_SEX": "Sexo", "HOURSLEEP": "Sono em noites de semana", "PHYSACTIV": "Atividade física", "MAKEFRIEND": "Dificuldade com amizades",
          "BULLIED_R": "Bullying sofrido", "BULLY": "Bullying praticado", "ano": "Ano da pesquisa", "faixa_etaria": "Faixa etária"}


def interface_paths(root, config_path=None):
    """Registro de modelos e pasta de relatórios usados pela interface (configs/interface.json)."""
    root = Path(root)
    config = json.loads(Path(config_path or root / "configs/interface.json").read_text(encoding="utf-8"))
    paths = {"registro": (root / config["registro"]).resolve(), "relatorios": (root / config["relatorios"]).resolve()}
    if (root / "models").resolve() not in paths["registro"].parents or paths["registro"].name != "registro.json":
        raise ValueError("Registro de modelos fora de models/")
    if paths["relatorios"] != (root / "reports").resolve() and (root / "reports").resolve() not in paths["relatorios"].parents:
        raise ValueError("Relatórios fora de reports/")
    return paths


def json_result(path, expected_sha):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("dataset_sha256") != expected_sha:
        raise ValueError("Resultados não correspondem ao dataset atual")
    return value


def distribution(frame, column, labels=None):
    values = frame[column].astype("string").fillna("Não informado")
    table = values.value_counts().rename_axis("categoria").reset_index(name="n")
    table = table.assign(ordem=pd.to_numeric(table.categoria, errors="coerce")).sort_values(["ordem", "categoria"], na_position="last").drop(columns="ordem")
    if labels:
        table["categoria"] = table.categoria.map(lambda x: labels.get(x, x))
    return table


def outcome_by(frame, column, target, labels=None):
    eligible = frame.loc[frame[target].notna(), [column, target]].copy()
    eligible[column] = eligible[column].astype("string").fillna("Não informado")
    table = eligible.groupby(column, dropna=False)[target].agg(n="count", positivos="sum").reset_index()
    table["proporcao_amostral"] = table["positivos"] / table.n
    if labels:
        table[column] = table[column].map(lambda x: labels.get(x, x))
    return table


def distribution_chart(frame, column, manifest):
    labels = manifest.get("rotulos", {}).get(column)
    if column in TARGETS:
        labels = {"0": "Sem relato atual", "1": "Com relato atual", "Não informado": "Indeterminado"}
    table = distribution(frame, column, labels)
    figure = px.bar(table, x="categoria", y="n", title=LABELS.get(column, column), color_discrete_sequence=["#6754bb"])
    figure.update_layout(xaxis_title="Categoria", yaxis_title="Registros amostrais", template="plotly_white")
    return figure


def load_figure(path):
    return pio.from_json(Path(path).read_text(encoding="utf-8"))


def filter_frame(frame, years, age_range, sexes):
    filtered = frame.loc[frame.ano.isin(years) & frame.SC_AGE_YEARS.between(*age_range) & frame.SC_SEX.isin(sexes)].copy()
    filtered["faixa_etaria"] = pd.cut(filtered.SC_AGE_YEARS, bins=[5, 11, 17], labels=["6–11", "12–17"])
    return filtered


def overview(frame):
    return {"registros": len(frame), "anos": sorted(int(y) for y in frame.ano.unique()),
            "targets": {target: {"positivos": int(frame[target].eq(1).sum()), "negativos": int(frame[target].eq(0).sum()),
                                 "indeterminados": int(frame[target].isna().sum())} for target in TARGETS}}


ROTINA_ROTULOS = {"SCREENTIME": "Tempo de tela", "HOURSLEEP": "Sono", "PHYSACTIV": "Atividade física", "MAKEFRIEND": "Dificuldade com amizades"}


def contribution_chart(contrib, target, modelo, tipo="incremental", foco="SCREENTIME"):
    """Diferença de ROC AUC (com − sem o fator) e IC, com todos os fatores de rotina lado a lado."""
    import plotly.graph_objects as go
    table = contrib.loc[contrib.target.eq(target) & contrib.modelo.eq(modelo) & contrib.tipo.eq(tipo)].sort_values("delta_auc")
    if table.empty:
        raise ValueError("Sem contribuições para a combinação pedida")
    labels = [ROTINA_ROTULOS.get(f, f) for f in table.fator]
    colors = ["#c4572a" if f == foco else "#4c6fa5" for f in table.fator]
    figure = go.Figure(go.Scatter(x=table.delta_auc, y=labels, mode="markers", marker={"size": 12, "color": colors},
                                  error_x={"type": "data", "symmetric": False, "array": table.delta_auc_ic_sup - table.delta_auc,
                                           "arrayminus": table.delta_auc - table.delta_auc_ic_inf, "color": "#8a8f9c"},
                                  hovertemplate="%{y}: %{x:.4f}<extra></extra>"))
    figure.add_vline(x=0, line_dash="dot", line_color="#8a8f9c")
    title = "Quanto cada fator acrescenta além dos demais" if tipo == "incremental" else "Quanto cada fator acrescenta sozinho a idade e sexo"
    figure.update_layout(title=f"{title} — {LABELS.get(target, target)}", template="plotly_white", showlegend=False,
                         xaxis_title="Diferença na ROC AUC (com − sem o fator)", yaxis_title="", height=320, margin={"l": 10, "r": 10})
    return figure


def routine_profile_chart(perfil, variavel, periodo="2020–2024"):
    """Distribuição ponderada (estimativa pontual) de um fator de rotina por faixa etária."""
    table = perfil.loc[perfil.variavel.eq(variavel) & perfil.periodo.astype(str).eq(periodo)].sort_values("categoria")
    if table.empty:
        raise ValueError("Sem perfil para a variável e o período pedidos")
    figure = px.bar(table, x="rotulo_categoria", y="percentual_ponderado", color="faixa_etaria", barmode="group",
                    color_discrete_sequence=["#4c6fa5", "#6b8c65"], labels={"rotulo_categoria": "", "percentual_ponderado": "% ponderado", "faixa_etaria": "Idade"},
                    title=f"{ROTINA_ROTULOS.get(variavel, variavel)} — NSCH {periodo}")
    figure.update_layout(template="plotly_white", height=340, margin={"l": 10, "r": 10})
    return figure


def routine_history_chart(frame, objetivos=()):
    """Tela e sono informados pela família no mesmo gráfico, com as linhas dos objetivos que ela escolheu."""
    import plotly.graph_objects as go
    figure = go.Figure()
    for column, name, color in [("tela_horas", "Tela recreativa", "#4c6fa5"), ("sono_horas", "Sono", "#6b8c65")]:
        points = frame.dropna(subset=[column])
        if not points.empty:
            figure.add_trace(go.Scatter(x=points.data, y=points[column], name=name, mode="lines+markers", line={"color": color}))
    for objetivo in objetivos:
        if objetivo["tipo"] in ("tela_max", "sono_min"):
            color = "#4c6fa5" if objetivo["tipo"] == "tela_max" else "#6b8c65"
            figure.add_hline(y=objetivo["valor"], line_dash="dash", line_color=color, annotation_text=objetivo["descricao"], annotation_position="top left")
    figure.update_layout(template="plotly_white", title="Tela e sono nos dias registrados", xaxis_title="Data", yaxis_title="Horas",
                         legend={"orientation": "h", "y": -0.2}, height=380)
    return figure
