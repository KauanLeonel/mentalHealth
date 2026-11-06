"""Análise descritiva não ponderada de dataset analítico aprovado."""

import argparse
from pathlib import Path

from mindscreen.dados_validados import TARGETS, load_dataset, safe_output


def run(manifest_path, output):
    manifest, df = load_dataset(manifest_path)
    import pandas as pd
    import plotly.express as px

    output = safe_output(output)
    output.mkdir(parents=True, exist_ok=True)
    df = df.copy()
    if "SC_AGE_YEARS" in df:
        df["faixa_etaria"] = pd.cut(pd.to_numeric(df["SC_AGE_YEARS"], errors="coerce"),
                                    bins=[-1, 5, 11, 17, float("inf")], labels=["0–5", "6–11", "12–17", "18+"])
    available = [x for x in ["ano", "SC_AGE_YEARS", "faixa_etaria", "SC_SEX", "SCREENTIME", *TARGETS,
                              "HOURSLEEP", "PHYSACTIV", "BULLIED_R", "BULLY", "MAKEFRIEND"] if x in df.columns]
    for target in TARGETS:
        if not df[target].dropna().isin([0, 1]).all():
            raise ValueError(f"{target} contém valores diferentes de 0, 1 e ausente")
    missing = df.isna().sum().rename("n_ausentes").to_frame()
    missing["percentual"] = missing["n_ausentes"] / len(df) * 100 if len(df) else 0
    missing.to_csv(output / "faltantes.csv", encoding="utf-8-sig")
    for column in available:
        counts = df[column].astype("string").fillna("[ausente]").value_counts(dropna=False).rename_axis("categoria").reset_index(name="n")
        counts["proporcao_amostral"] = counts["n"] / len(df) if len(df) else 0
        counts["categoria_pouco_frequente"] = counts["proporcao_amostral"] < 0.01
        counts.to_csv(output / f"distribuicao_{column}.csv", index=False, encoding="utf-8-sig")
        if column != "SC_AGE_YEARS":
            px.bar(counts, x="categoria", y="n", title=f"Distribuição amostral: {column}").write_html(output / f"distribuicao_{column}.html", include_plotlyjs="directory")
    for target in TARGETS:
        for variable in ["SCREENTIME", "ano", "HOURSLEEP", "PHYSACTIV", "BULLIED_R", "BULLY", "MAKEFRIEND"]:
            if variable not in df:
                continue
            eligible = df.loc[df[target].notna(), [variable, target]].copy()
            eligible[variable] = eligible[variable].astype("string").fillna("[ausente]")
            table = eligible.groupby(variable, dropna=False)[target].agg(n="count", positivos="sum").reset_index()
            table["proporcao_positivos"] = table["positivos"] / table["n"]
            table.to_csv(output / f"{target}_por_{variable}.csv", index=False, encoding="utf-8-sig")
            if not table.empty:
                px.bar(table, x=variable, y="proporcao_positivos", hover_data=["n", "positivos"],
                       title=f"Proporção amostral de {target} por {variable}").write_html(output / f"{target}_por_{variable}.html", include_plotlyjs="directory")
    lines = ["# Análise exploratória", "", f"Registros analisados: {len(df)}.",
             "", "Todas as contagens e proporções são amostrais e não ponderadas. Não são estimativas populacionais; não foram calculados intervalos de confiança.",
             "As proporções por desfecho excluem apenas valores ausentes do próprio desfecho; categorias ausentes do fator são apresentadas separadamente.",
             "Valores inferiores a 1% da amostra são sinalizados como pouco frequentes. As categorias seguem a codificação do dataset validado.",
             "Os dados de 2024 são apresentados apenas para descrição; não use seus resultados para selecionar variáveis, hiperparâmetros, limiares ou modelos.",
             "Associação observada não estabelece causalidade e não equivale a diagnóstico.", "", "## Contagens por ano"]
    lines.extend(f"- {year}: {count}" for year, count in df["ano"].value_counts().sort_index().items())
    for target in TARGETS:
        counts = df[target].value_counts(dropna=False).to_dict()
        lines.extend(["", f"## {target}", f"- Positivos: {counts.get(1, 0)}; negativos: {counts.get(0, 0)}; ausentes: {int(df[target].isna().sum())}."])
    lines.extend(["", "Consulte as tabelas para frequências, desbalanceamento e comparações; a interpretação de diferenças depende de revisão metodológica, tamanhos de grupo e desenho da pesquisa.",
                  f"Documento de validação declarado: {manifest['documentacao_validacao']}."])
    (output / "relatorio.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/exploratoria"))
    args = parser.parse_args()
    run(args.manifesto, args.output)


if __name__ == "__main__":
    main()
