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
